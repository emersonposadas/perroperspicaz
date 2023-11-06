import os
import re
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters
import openai

# Load environment variables from .env file
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_TOKEN = os.getenv('OPENAI_TOKEN')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
OPENAI_ENGINE = os.getenv('OPENAI_ENGINE')
FALLACY_PROMPT = os.getenv('FALLACY_PROMPT')  # Add this line to read the prompt from .env

# Initialize OpenAI
openai.api_key = OPENAI_TOKEN

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL),
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Handler function for the /start command
async def start(update: Update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Hi! Reply to a message with 🤔 and I will analyze it for logical fallacies.")

# Handler function to detect thinking emoji and process the text
async def detect_fallacy(update: Update, context):
    # Extract the text from the message replied to with a thinking emoji
    if update.message.reply_to_message and '🤔' in update.message.text:
        replied_message = update.message.reply_to_message
        message_text = replied_message.text
        logger.info(f"Received a thinking emoji reply. Analyzing text: {message_text}")

        # Call OpenAI API to process the text
        try:
            response = openai.Completion.create(
                engine=OPENAI_ENGINE,
                prompt=f"{FALLACY_PROMPT}\n\n{message_text}\n\n",
                max_tokens=150,
                temperature=0.5
            )

            answer = response.choices[0].text.strip() if response.choices else "No logical fallacies detected."
            # Use 'reply_to_message_id' to quote the source message
            await update.message.reply_text(answer, reply_to_message_id=replied_message.message_id)
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            await update.message.reply_text("An error occurred while analyzing the text.", reply_to_message_id=replied_message.message_id)
    else:
        logger.info("No replied message found.")


# Main function to set up the bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Command handler for the /start command
    application.add_handler(MessageHandler(filters.Command('start'), start))

    # Message handler for detecting the thinking face emoji reaction
    application.add_handler(MessageHandler(filters.Regex(re.compile(r'[\U0001F914]')) & filters.UpdateType.MESSAGES, detect_fallacy))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()
