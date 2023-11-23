"""
bot_utils.py

This module contains utility functions used across the Telegram bot application. 
It includes functions for sending replies, handling common bot operations, and 
managing environment configurations. The functions in this module are designed 
to be reusable and are used by various handlers and commands in the bot's workflow.

Functions:
    send_reply(update: Update, context, text: str): Asynchronously sends a reply 
    to a Telegram message based on the chat type and configuration.
"""
import logging
import os
from telegram import Update
from telegram.constants import ParseMode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fetch and set the PP_REPLY_TO_PRIVATE variable
PP_REPLY_TO_PRIVATE = os.getenv('PP_REPLY_TO_PRIVATE', 'false').lower() == 'true'

logger = logging.getLogger(__name__)

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
    if update.message.chat.type == 'private':
        if PP_REPLY_TO_PRIVATE:
            # Send a private reply
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
            logger.info("Sent private reply.")
        else:
            # Do not reply to private messages
            logger.info("Not replying to private message as PP_REPLY_TO_PRIVATE is False.")
    else:
        # Reply in the chat group
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        logger.info("Sent public reply.")
