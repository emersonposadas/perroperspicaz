import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import openai

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_TOKEN = os.getenv('OPENAI_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
OPENAI_ENGINE = os.getenv('OPENAI_ENGINE')
FALLACY_PROMPT = os.getenv('FALLACY_PROMPT')  # Assuming you have a specific prompt for fallacy detection

# OpenAI API configuration
openai.api_key = OPENAI_TOKEN

# Logging configuration
logging.basicConfig(level=getattr(logging, LOG_LEVEL),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Function to send a welcome message
async def start(update: Update, context):
    welcome_text = "Hi! Reply to a message with 🤔 and I will analyze it for logical fallacies."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text)

# Function to analyze a message for logical fallacies
async def analyze_fallacy(text):
    try:
        response = openai.Completion.create(
            engine=OPENAI_ENGINE,
            prompt=f"{FALLACY_PROMPT}\n\n{text}\n\n",
            max_tokens=150,
            temperature=0.5
        )
        return response.choices[0].text.strip() if response.choices else "No logical fallacies detected."
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API error: {e}")
        return "An error occurred while analyzing the text."

# Function to detect logical fallacies when the thinking emoji is used
async def detect_fallacy(update: Update, context):
    replied_message = update.message.reply_to_message
    if replied_message and '🤔' in update.message.text:
        message_text = replied_message.text
        logger.info(f"Analyzing text: {message_text}")
        
        answer = await analyze_fallacy(message_text)
        await update.message.reply_text(answer, reply_to_message_id=replied_message.message_id)
    else:
        logger.info("No replied message or thinking emoji found.")

# Main function to set up the bot handlers and run the bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    start_handler = MessageHandler(filters.Command('start'), start)
    fallacy_handler = MessageHandler(filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES, detect_fallacy)

    application.add_handler(start_handler)
    application.add_handler(fallacy_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
