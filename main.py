import os
import re
import logging
import random
import time
import json
from dotenv import load_dotenv
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, CallbackContext
from newsapi import NewsApiClient
from urllib.parse import parse_qs
import openai

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_TOKEN = os.getenv('OPENAI_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
ENABLE_FILE_LOGGING = os.getenv('ENABLE_FILE_LOGGING', 'false').lower() == 'true'
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', 'bot.log')
OPENAI_ENGINE = os.getenv('OPENAI_ENGINE', 'gpt-4')
FALLACY_PROMPT = os.getenv('FALLACY_PROMPT')
REPLY_TO_PRIVATE = os.getenv('REPLY_TO_PRIVATE', 'false').lower() == 'true'
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY')
NEWSAPI_PAGESIZE = int(os.getenv('NEWSAPI_PAGESIZE', '50'))

# Initialize NewsAPI
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

# OpenAI API configuration
openai.api_key = OPENAI_TOKEN

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

if ENABLE_FILE_LOGGING:
    file_handler = logging.FileHandler(LOG_FILE_PATH)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    logger = logging.getLogger(__name__)

def setup_openai_response(prompt_template, message_text):
    try:
        response = openai.Completion.create(
            engine=OPENAI_ENGINE,
            prompt=f"{prompt_template}\n\n{message_text}\n\n",
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].text.strip() if response.choices else "No clear answer detected."
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "An error occurred while processing the text."

async def start(update: Update, context):
    welcome_text = ("Hi there! I can help you with logical fallacies and news.\n"
                    "Reply to a message with 🤔 to analyze for logical fallacies.\n"
                    "Use /news get a random article.")
    await send_reply(update, context, welcome_text)

async def detect_fallacy(update: Update, context):
    replied_message = update.message.reply_to_message
    if replied_message:
        logger.info(f"Analyzing for fallacies: {replied_message.text}")
        answer = setup_openai_response(FALLACY_PROMPT, replied_message.text)
        await send_reply(update, context, answer)

def fetch_news(query_params):
    query_params['page_size'] = NEWSAPI_PAGESIZE
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
        news_response = fetch_news({default_param: default_value, 'page_size': NEWSAPI_PAGESIZE})
        if news_response['articles']:
            random_article = random.choice(news_response['articles'])
            formatted_response = format_single_article_response(random_article)
            logger.info(f"Randomly selected item: {random_article['title']}")
    else:
        query_params = {
            'q': user_input,
            'page_size': NEWSAPI_PAGESIZE
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
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    start_handler = CommandHandler('start', start)
    fallacy_handler = MessageHandler(filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES, detect_fallacy)
    news_handler = CommandHandler('news', handle_news_request)

    # Register handlers with the application
    application.add_handler(start_handler)
    application.add_handler(fallacy_handler)
    application.add_handler(news_handler)

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
