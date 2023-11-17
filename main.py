"""
This module integrates various functionalities including environment variable management, 
logging, random operations, time tracking, data serialization, Telegram bot interactions, 
Google API client interactions, and news data retrieval. It sets up handlers for Telegram 
messages and commands, provides capabilities for Google API authentication and error handling, 
and enables access to news information using the News API.
"""
import os
import re
import logging
import random
import time
import pickle
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    CommandHandler,
    CallbackContext
)
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from news_handler import fetch_bing_news, summarize_with_gpt4
from fx_handlers import fx_command
import openai

# Load environment variables from .env file
load_dotenv()
PP_TELEGRAM_TOKEN = os.getenv('PP_TELEGRAM_TOKEN')
PP_OPENAI_TOKEN = os.getenv('PP_OPENAI_TOKEN')
PP_LOG_LEVEL = os.getenv('PP_LOG_LEVEL', 'INFO').upper()
PP_ENABLE_FILE_LOGGING = os.getenv('PP_ENABLE_FILE_LOGGING', 'false').lower() == 'true'
PP_LOG_FILE_PATH = os.getenv('PP_LOG_FILE_PATH', 'bot.log')
PP_OPENAI_ENGINE = os.getenv('PP_OPENAI_ENGINE', 'gpt-4')
PP_FALLACY_PROMPT = os.getenv('PP_FALLACY_PROMPT')
PP_REPLY_TO_PRIVATE = os.getenv('PP_REPLY_TO_PRIVATE', 'false').lower() == 'true'
PP_WELCOME_TEXT = os.getenv('PP_WELCOME_TEXT')
PP_NEWSAPI_KEY = os.getenv('PP_NEWSAPI_KEY')
PP_NEWSAPI_PAGESIZE = int(os.getenv('PP_NEWSAPI_PAGESIZE', '50'))
PP_YT_PLAYLIST_ID = os.getenv('PP_YT_PLAYLIST_ID')
PP_YT_AWAITING_LINK = {}

# Initialize NewsAPI
newsapi = NewsApiClient(api_key=PP_NEWSAPI_KEY)

# OpenAI API configuration
openai.api_key = PP_OPENAI_TOKEN

# Apply logging filter and configuration
class NoHTTPRequestFilter(logging.Filter):
    """
    A custom logging filter that excludes log records starting with 'HTTP Request:'.

    This filter can be used to prevent logging of HTTP requests, keeping the log output 
    cleaner and more focused on application-specific messages.
    """
    def filter(self, record):
        return not record.getMessage().startswith('HTTP Request:')

# Apply the filter to httpx logger
httpx_logger = logging.getLogger('httpx')
httpx_logger.addFilter(NoHTTPRequestFilter())

# Logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

if PP_ENABLE_FILE_LOGGING:
    file_handler = logging.FileHandler(PP_LOG_FILE_PATH)
    file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger(__name__)

def setup_openai_response(prompt_template, message_text):
    """
    Generate a response from OpenAI's GPT model based on a given prompt and message.

    The function formats the input by combining a predefined prompt template with 
    the message text, and then sends this to OpenAI's API. It handles any potential 
    API errors and returns the generated response or an appropriate error message.

    Args:
        prompt_template (str): A predefined template to which the message text is appended.
        message_text (str): The message text to be processed by the OpenAI API.

    Returns:
        str: The response generated by OpenAI or an error message.
    """
    try:
        response = openai.Completion.create(
            engine=PP_OPENAI_ENGINE,
            prompt=f"{prompt_template}\n\n{message_text}\n\n",
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].text.strip() if response.choices else "No clear answer detected."
    except openai.error.OpenAIError as e:
        logger.error("OpenAI API error: %s", e)
        return "An error occurred while processing the text."

def add_song_to_playlist(song_url, playlist_id):
    """
    Adds a song to a specified YouTube playlist.

    This function authenticates with YouTube, extracts the video ID from the given song URL,
    and then attempts to add the song to the specified playlist. It handles potential errors
    and logs the outcome of the operation.

    Args:
        song_url (str): The URL of the song to be added.
        playlist_id (str): The ID of the YouTube playlist to which the song will be added.

    Returns:
        str: A message indicating the result of the operation - whether the song was 
        successfully added, or an error occurred.
    """
    # Authenticate and get YouTube service
    youtube = get_authenticated_service()

    # Extract the video ID from the YouTube URL
    video_id = extract_video_id(song_url)
    if not video_id:
        return "Invalid YouTube URL."

    try:
        request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id
                    }
                }
            }
        )
        response = request.execute()
        logger.info("Added video with ID %s to playlist %s", video_id, playlist_id)
        return f"Song added to playlist: {response['snippet']['title']}"
    except HttpError as e:
        logger.error("Error adding song to playlist: %s", e)
        return "Failed to add song to playlist."

async def add_song(update: Update, context: CallbackContext):
    """
    Initiates the process of adding a song to a user-specific list by
    setting a flag and prompting the user for a YouTube link.

    This asynchronous function is triggered by a user command. It sets a flag indicating
    that the bot is awaiting a YouTube link from the user. It then sends a message to the
    user asking for the link.

    Args:
        update (Update): An object that represents an incoming update.
        context (CallbackContext): An object that provides context about the command.

    Returns:
        None: This function does not return any value. It sends a message to the user.
    """
    user_id = update.effective_user.id
    PP_YT_AWAITING_LINK[user_id] = True  # Set the flag to True for this user
    await update.message.reply_text("Please send the YouTube link.")

async def receive_youtube_link(update: Update, context: CallbackContext):
    """
    Handles the reception of a YouTube link from a user and attempts to add it to a playlist.

    This asynchronous function checks if the bot is awaiting a YouTube link from the user. If so, 
    it processes the received link, attempts to add it to a predefined playlist, and communicates 
    the result back to the user. It then resets the awaiting-link flag for the user.

    Args:
        update (Update): An object that contains the incoming update data.
        context (CallbackContext): Provides context about the update such as the user's data.

    Returns:
        None: This function primarily interacts through Telegram messages and does
        not return a value.
    """
    user_id = update.message.from_user.id

    if PP_YT_AWAITING_LINK.get(user_id):
        youtube_link = update.message.text
        logger.info("Received YouTube link %s", youtube_link)

        result = add_song_to_playlist(youtube_link, PP_YT_PLAYLIST_ID)
        await update.message.reply_text(result)

        PP_YT_AWAITING_LINK[user_id] = False  # Reset the flag
        logger.info("Processed YouTube link: %s", youtube_link)
    else:
        # Ignore other messages
        pass

async def get_song(update: Update, context: CallbackContext):
    """
    Asynchronously selects a random song from a YouTube playlist and sends its URL to the user.

    This function authenticates with YouTube, fetches the details of a specified playlist,
    and randomly selects a song from this playlist. It then sends a message to the user with 
    the title of the song and a link to it on YouTube. The function handles potential errors 
    in fetching playlist details or during random song selection and communicates the outcome 
    to the user.

    Args:
        update (Update): An object representing an incoming update.
        context (CallbackContext): An object providing context about the update.

    Returns:
        None: This function sends messages to the user and does not return any value.
    """
    # Authenticate and get YouTube service
    youtube = get_authenticated_service()
    playlist_id = PP_YT_PLAYLIST_ID

    try:
        # Get total number of songs in the playlist
        playlist_details = youtube.playlists().list(
            part="contentDetails",
            id=playlist_id
        ).execute()

        total_songs = playlist_details["items"][0]["contentDetails"]["itemCount"]

        # Randomly select a song index
        random_index = random.randint(1, total_songs)

        # Calculate the page token
        page_token = None
        items_per_page = 50  # Adjust as needed
        current_page = 0

        if random_index > items_per_page:
            target_page = random_index // items_per_page

            while current_page < target_page:
                response = youtube.playlistItems().list(
                    part="snippet",
                    playlistId=playlist_id,
                    maxResults=items_per_page,
                    pageToken=page_token
                ).execute()

                page_token = response.get("nextPageToken")
                current_page += 1

                # Break the loop if there's no more pages but we haven't reached the target page
                if not page_token:
                    break

        # Now page_token is set to the page where the random song is located
        # Retrieve the specific song
        response = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=items_per_page,
            pageToken=page_token  # Use the calculated page token
        ).execute()

        # Calculate the index of the song in the current page
        song_index_in_page = random_index % items_per_page - 1
        if song_index_in_page < 0:
            song_index_in_page += items_per_page

        selected_song = response["items"][song_index_in_page]
        title = selected_song["snippet"]["title"]
        video_id = selected_song["snippet"]["resourceId"]["videoId"]
        song_url = f"https://www.youtube.com/watch?v={video_id}"

        await update.message.reply_text(
            f"🎶 Here's a tune I picked just for you!: {title}\n"
            f"🔗 Tap to listen: {song_url}"
        )
        logger.info("Recommended song: %s URL: %s", title, song_url)
    except HttpError as e:
        logger.error("Error fetching songs from playlist: %s", e)
        await update.message.reply_text("Failed to fetch song from playlist.")
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e, exc_info=True)
        await update.message.reply_text("An error occurred while processing your request.")


def extract_video_id(song_url):
    """
    Extracts the video ID from a given YouTube URL.

    This function uses a regular expression to match and extract the video ID from
    various formats of YouTube URLs. It supports standard YouTube URLs, shortened 
    youtu.be URLs, and YouTube Music URLs. If the URL does not match any of the 
    expected formats, it returns None and prints an error message.

    Args:
        song_url (str): The YouTube URL from which the video ID needs to be extracted.

    Returns:
        str or None: The extracted video ID if the URL is valid, or None if the URL is invalid.
    """
    # This regex pattern is for standard YouTube video URLs
    regex_pattern = (
        r'(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)'
        r'([a-zA-Z0-9_-]+)'
    )
    match = re.search(regex_pattern, song_url)

    if match:
        return match.group(1)

    # Handle the case where the URL is not a standard YouTube URL
    print("Invalid YouTube URL.")
    return None

def get_authenticated_service():
    """
    Creates and returns an authenticated YouTube service client.

    The function attempts to load existing credentials from a pickle file. If the credentials
    are not found or are invalid, it tries to refresh them. It finally creates and returns a 
    YouTube service client using these credentials.

    Returns:
        googleapiclient.discovery.Resource: An authenticated YouTube service client.
    """
    creds = None
    token_file = 'token.pickle'

    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)

    return build('youtube', 'v3', credentials=creds)

async def start(update: Update, context):
    """
    Sends a welcome message to the user when they initiate a conversation with the bot.

    This asynchronous function is triggered when a user starts interaction with the bot. It
    retrieves a predefined welcome text and uses another function to send this message to the user.

    Args:
        update (Update): An object representing an incoming update.
        context: The context passed by the Telegram bot framework.
    
    Returns:
        None: The function sends a message to the user but does not return any value.
    """
    welcome_text = PP_WELCOME_TEXT
    await send_reply(update, context, welcome_text)

async def detect_fallacy(update: Update, context):
    """
    Analyzes a message for logical fallacies and sends a response.

    This asynchronous function is invoked to analyze the text of a replied-to message in
    a chat for logical fallacies. It uses an OpenAI-based setup to generate an analysis
    of the text. If a replied-to message is found, it logs the analysis process, gets a
    response from OpenAI, and sends this response back to the chat.

    Args:
        update (Update): An object representing an incoming update.
        context: The context passed by the Telegram bot framework.
    
    Returns:
        None: The function sends a response message to the chat but does not return any value.
    """
    replied_message = update.message.reply_to_message
    if replied_message:
        logger.info("Analyzing for fallacies: %s", replied_message.text)
        answer = setup_openai_response(PP_FALLACY_PROMPT, replied_message.text)
        await send_reply(update, context, answer)

async def send_reply(update: Update, context, text: str):
    """
    Sends a reply to a Telegram message either in private or in the same chat.

    This asynchronous function determines the type of chat from which the message originated 
    and sends a reply accordingly. If the chat is private and the bot is configured to reply 
    to private messages, it sends a private message. Otherwise, it replies in the same chat.

    Args:
        update (Update): An object representing an incoming update.
        context: The context passed by the Telegram bot framework, used to send messages.
        text (str): The text to be sent as a reply.

    Returns:
        None: This function sends a message but does not return any value.
    """
    if update.message.chat.type == 'private' and PP_REPLY_TO_PRIVATE:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        logger.info("Sent private reply.")
    else:
        await update.message.reply_text(text)
        logger.info("Sent public reply.")

def main():
    """
    Main function for running the Telegram bot application.

    This function sets up the Telegram bot application, registers command and message handlers, 
    and continuously runs the bot to interact with users. It handles network errors gracefully 
    by retrying after a brief delay and exits the loop for unexpected errors.

    The following handlers are registered:
    - 'start_handler' for handling the "/start" command.
    - 'fallacy_handler' for detecting messages containing the "🤔" emoji.
    - 'news_handler' for handling the "/news" command and news-related requests.
    - 'get_song_handler' for handling the "/getsong" command and recommending songs.
    - 'add_song_handler' for handling the "/addsong" command and adding songs to a playlist.
    - 'youtube_link_handler' for handling text messages that are not commands.

    Args:
        None: This function takes no arguments.

    Returns:
        None: This function continuously runs the Telegram bot application and does not
        return a value.
    """
    application = ApplicationBuilder().token(PP_TELEGRAM_TOKEN).build()

    # Handlers
    start_handler = CommandHandler('start', start)
    fallacy_handler = MessageHandler(
        filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES,
        detect_fallacy
    )
    news_handler = CommandHandler('news', handle_news_request)
    get_song_handler = CommandHandler('getsong', get_song)
    add_song_handler = CommandHandler('addsong', add_song)
    youtube_link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, receive_youtube_link)
    fx_handler = CommandHandler('fx', fx_command)

    # Register handlers with the application
    application.add_handler(start_handler)
    application.add_handler(fallacy_handler)
    application.add_handler(news_handler)
    application.add_handler(get_song_handler)
    application.add_handler(add_song_handler)
    application.add_handler(youtube_link_handler)
    application.add_handler(fx_handler)

    while True:
        try:
            application.run_polling()
        except telegram.error.NetworkError as e:
            logger.error("Network error encountered: %s", e)
            time.sleep(5)  # Wait for 5 seconds before retrying
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            break  # Exit the loop for unexpected errors

if __name__ == '__main__':
    main()
