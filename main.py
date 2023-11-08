import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler
import openai

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_TOKEN = os.getenv('OPENAI_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
OPENAI_ENGINE = os.getenv('OPENAI_ENGINE')
FALLACY_PROMPT = os.getenv('FALLACY_PROMPT')
MUSIC_PROMPT = os.getenv('MUSIC_PROMPT')
REPLY_TO_PRIVATE = os.getenv('REPLY_TO_PRIVATE', 'false').lower() == 'true'

# OpenAI API configuration
openai.api_key = OPENAI_TOKEN

# Logging filter to exclude 'HTTP Request:' logs
class NoHTTPRequestFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('HTTP Request:')

# Apply the filter to httpx logger
httpx_logger = logging.getLogger('httpx')
httpx_logger.addFilter(NoHTTPRequestFilter())

# Logging configuration
logging.basicConfig(level=getattr(logging, LOG_LEVEL),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    welcome_text = ("Hi there! I can help you with logical fallacies and music recommendations.\n"
                    "Reply to a message with 🤔 to analyze for logical fallacies.\n"
                    "Use /music followed by your mood or preference to get music recommendations.")
    await send_reply(update, context, welcome_text)

async def detect_fallacy(update: Update, context):
    replied_message = update.message.reply_to_message
    if replied_message:
        logger.info(f"Analyzing for fallacies: {replied_message.text}")
        answer = setup_openai_response(FALLACY_PROMPT, replied_message.text)
        await send_reply(update, context, answer)

async def recommend_music(update: Update, context):
    user_input = ' '.join(context.args)
    if user_input:
        logger.info(f"Recommending music for: {user_input}")
        recommendation = setup_openai_response(MUSIC_PROMPT, user_input)
        await send_reply(update, context, recommendation)

async def send_reply(update: Update, context, text: str):
    if update.message.chat.type == 'private' and REPLY_TO_PRIVATE:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        logger.info("Sent private reply.")
    else:
        await update.message.reply_text(text)
        logger.info("Sent public reply.")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Handlers
    start_handler = CommandHandler('start', start)
    fallacy_handler = MessageHandler(filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES, detect_fallacy)
    music_handler = CommandHandler('music', recommend_music)

    # Register handlers with the application
    application.add_handler(start_handler)
    application.add_handler(fallacy_handler)
    application.add_handler(music_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
