"""
Module to handle foreign exchange rate commands in the Telegram bot.
"""
import os
import logging
from telegram import Update
from telegram.ext import CallbackContext
import freecurrencyapi
from dotenv import load_dotenv
from bot_utils import send_reply

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

PP_FXAPI_KEY = os.getenv('PP_FXAPI_KEY')

# Initialize the Free Currency API client
client = freecurrencyapi.Client(PP_FXAPI_KEY)

def fetch_exchange_rate(base_currency, target_currency):
    """
    Fetches the exchange rate between two currencies using freecurrencyapi.com.

    Args:
        base_currency (str): The base currency code.
        target_currency (str): The target currency code.

    Returns:
        float: The exchange rate, or None if an error occurs.
    """
    try:
        logger.info("Fetching latest exchange rates for %s to %s", base_currency, target_currency)
        latest_rates = client.latest()

        if base_currency not in latest_rates['data'] or \
                target_currency not in latest_rates['data']:
            logger.error("Currency not found in latest rates data.")
            return None

        base_rate = latest_rates['data'].get(base_currency, 1)
        target_rate = latest_rates['data'][target_currency]

        # Convert the base currency to the target currency
        exchange_rate = target_rate / base_rate
        return exchange_rate
    except Exception as e:
        logger.error("Exception in fetch_exchange_rate: %s", e)
        return None

async def fx_command(update: Update, context: CallbackContext):
    """
    Handles the /fx command in the Telegram bot.

    Args:
        update (Update): An object representing an incoming update.
        context (CallbackContext): The context passed by the Telegram bot framework.
    """
    args = context.args
    if len(args) != 2:
        await update.message.reply_text("Please provide two currency codes. Usage: /fx USD EUR")
        return

    base_currency, target_currency = args
    logger.info("Received /fx command for %s to %s", base_currency, target_currency)
    exchange_rate = fetch_exchange_rate(base_currency.upper(), target_currency.upper())

    if exchange_rate is not None:
        response_message = (
            f"Exchange rate from {base_currency.upper()} to {target_currency.upper()}: "
            f"{exchange_rate:.2f}"
        )
        logger.info("Successfully retrieved exchange rate.")
    else:
        response_message = "Unable to retrieve the exchange rate at the moment."
        logger.warning("Failed to retrieve exchange rate.")

    await send_reply(update, context, response_message)
