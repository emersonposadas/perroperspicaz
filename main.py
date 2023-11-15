import os
import re
import logging
import random
import time
import pickle
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    MessageHandler, 
    filters, 
    CommandHandler, 
    CallbackContext, 
    CallbackQueryHandler
)
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from newsapi import NewsApiClient
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
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger(__name__)

def setup_openai_response(prompt_template, message_text):
    try:
        response = openai.Completion.create(
            engine=PP_OPENAI_ENGINE,
            prompt=f"{prompt_template}\n\n{message_text}\n\n",
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].text.strip() if response.choices else "No clear answer detected."
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "An error occurred while processing the text."

def add_song_to_playlist(song_url, playlist_id):
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
        logger.info(f"Added video with ID {video_id} to playlist {playlist_id}")
        return f"Song added to playlist: {response['snippet']['title']}"
    except HttpError as e:
        logger.error(f"Error adding song to playlist: {e}")
        return "Failed to add song to playlist."

async def add_song(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    PP_YT_AWAITING_LINK[user_id] = True  # Set the flag to True for this user
    await update.message.reply_text("Please send the YouTube link.")

async def send_youtube_link_button(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Send YouTube Link", callback_data='send_yt_link')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Please click the button to send a YouTube link:', reply_markup=reply_markup)
    logger.info("Sent YouTube link button.")

async def handle_callback_query(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'send_yt_link':
        user_id = query.from_user.id
        PP_YT_AWAITING_LINK[user_id] = True
        await query.edit_message_text(text="Please send the YouTube link now.")
        logger.info("Prompted for YouTube link.")

async def receive_youtube_link(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if PP_YT_AWAITING_LINK.get(user_id):
        youtube_link = update.message.text
        logger.info(f"Received YouTube link {youtube_link}")

        result = add_song_to_playlist(youtube_link, PP_YT_PLAYLIST_ID)
        await update.message.reply_text(result)

        PP_YT_AWAITING_LINK[user_id] = False  # Reset the flag
        logger.info(f"Processed YouTube link: {youtube_link}")
    else:
        # Ignore other messages
        pass

async def get_song(update: Update, context: CallbackContext):
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
            target_page = (random_index // items_per_page)

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

        await update.message.reply_text(f"🎶 Here's a tune I picked just for you!: {title}\n🔗 Tap to listen: {song_url}")
        logger.info(f"Recommended song: {title} URL: {song_url}")
    except HttpError as e:
        logger.error(f"Error fetching songs from playlist: {e}")
        await update.message.reply_text("Failed to fetch song from playlist.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        await update.message.reply_text("An error occurred while processing your request.")

def extract_video_id(song_url):
    # This regex pattern is for standard YouTube video URLs
    regex_pattern = r'(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)'
    match = re.search(regex_pattern, song_url)

    if match:
        return match.group(1)
    else:
        # Handle the case where the URL is not a standard YouTube URL
        print("Invalid YouTube URL.")
        return None

def get_authenticated_service():
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
    welcome_text = PP_WELCOME_TEXT
    await send_reply(update, context, welcome_text)

async def detect_fallacy(update: Update, context):
    replied_message = update.message.reply_to_message
    if replied_message:
        logger.info(f"Analyzing for fallacies: {replied_message.text}")
        answer = setup_openai_response(PP_FALLACY_PROMPT, replied_message.text)
        await send_reply(update, context, answer)

async def send_reply(update: Update, context, text: str):
    if update.message.chat.type == 'private' and PP_REPLY_TO_PRIVATE:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        logger.info("Sent private reply.")
    else:
        await update.message.reply_text(text)
        logger.info("Sent public reply.")

def fetch_news(query_params):
    query_params['page_size'] = PP_NEWSAPI_PAGESIZE
    articles = newsapi.get_everything(**query_params)
    return articles

def format_single_article_response(article):
    title = article.get('title', 'No Title')
    url = article.get('url', '#')
    return f"<a href='{url}'>{title}</a>"

def format_multiple_articles_response(articles):
    formatted_articles = ["• <a href='{url}'>{title}</a>".format(
        url=article.get('url', '#'), title=article.get('title', 'No Title')) for article in articles]
    return '\n'.join(formatted_articles)

async def handle_news_request(update: Update, context: CallbackContext):
    user_input = ' '.join(context.args)
    formatted_response = "No news relevant to your request has been found."

    if not user_input:
        default_param = 'q'
        default_value = 'general'
        logger.info(f"Performing news search with default parameter: {default_value}")
        news_response = fetch_news({default_param: default_value, 'page_size': PP_NEWSAPI_PAGESIZE})
        if news_response['articles']:
            random_article = random.choice(news_response['articles'])
            formatted_response = format_single_article_response(random_article)
            logger.info(f"Randomly selected item: {random_article['title']}")
    else:
        query_params = {
            'q': user_input,
            'page_size': PP_NEWSAPI_PAGESIZE
        }
        logger.info(f"Performing news search with user parameters: {query_params}")
        try:
            news_response = newsapi.get_everything(**query_params)
            if news_response['articles']:
                selected_articles = random.sample(news_response['articles'], min(5, len(news_response['articles'])))
                formatted_response = format_multiple_articles_response(selected_articles)
                logger.info(f"Selected articles: {[article['title'] for article in selected_articles]}")
        except Exception as e:
            logger.error(f"Error when querying the News API: {e}")

    await update.message.reply_text(formatted_response, parse_mode='HTML', disable_web_page_preview=True)

def main():
    application = ApplicationBuilder().token(PP_TELEGRAM_TOKEN).build()

    # Handlers
    start_handler = CommandHandler('start', start)
    fallacy_handler = MessageHandler(filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES, detect_fallacy)
    news_handler = CommandHandler('news', handle_news_request)
    get_song_handler = CommandHandler('getsong', get_song)
    add_song_handler = CommandHandler('addsong', add_song)
    callback_query_handler = CallbackQueryHandler(handle_callback_query)
    youtube_link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, receive_youtube_link)

    # Register handlers with the application
    application.add_handler(start_handler)
    application.add_handler(fallacy_handler)
    application.add_handler(news_handler)
    application.add_handler(get_song_handler)
    application.add_handler(add_song_handler)
    application.add_handler(callback_query_handler)
    application.add_handler(youtube_link_handler)

    while True:
       try:
           application.run_polling()
       except telegram.error.NetworkError as e:
           logger.error(f"Network error encountered: {e}")
           time.sleep(5)  # Wait for 5 seconds before retrying
       except Exception as e:
           logger.error(f"Unexpected error: {e}")
           break  # Exit the loop for unexpected errors

if __name__ == '__main__':
    main()