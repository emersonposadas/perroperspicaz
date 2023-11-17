import os
import requests
import logging
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PP_BING_NEWS_API_KEY = os.getenv('PP_BING_NEWS_API_KEY')
PP_OPENAI_TOKEN = os.getenv('PP_OPENAI_TOKEN')
PP_SUMMARIZATION_PROMPT = os.getenv('PP_SUMMARIZATION_PROMPT')
PP_OPENAI_ENGINE = os.getenv('PP_OPENAI_ENGINE', 'gpt-4')
PP_BING_NEWS_ENDPOINT = os.getenv('PP_BING_NEWS_ENDPOINT')

openai.api_key = PP_OPENAI_TOKEN
logger = logging.getLogger(__name__)

def fetch_bing_news(query):
    headers = {
        'Ocp-Apim-Subscription-Key': PP_BING_NEWS_API_KEY
    }
    params = {
        'q': query,
        'count': 5,
        'mkt': 'es-MX'
    }

    try:
        response = requests.get(PP_BING_NEWS_ENDPOINT, headers=headers, params=params)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        news_result = response.json()

        # Log detailed news results for debugging
        logger.debug("News Result: %s", news_result)

        articles = news_result.get('value', [])
        if not articles:
            logger.error("No news results found.")
            return []

        logger.info("Fetched news articles from Bing News API.")
        return articles
    except requests.RequestException as e:
        logger.error(f"Error fetching news: {e}")
        return []

async def summarize_with_gpt4(articles, send_reply_func):
    # Combine the titles and descriptions of all articles into one text
    combined_text = ' '.join([f"{article['name']}. {article['description']}" for article in articles])

    # Construct the prompt for summarization
    prompt = PP_SUMMARIZATION_PROMPT + combined_text

    try:
        response = openai.Completion.create(
            engine=PP_OPENAI_ENGINE,
            prompt=prompt,
            max_tokens=350,
            temperature=0.5
        )
        # Extract the summary text
        summary = response.choices[0].text.strip() if response.choices else "No clear summary available."

        # Log the summary generation
        logger.info("Generated summary using %s.", PP_OPENAI_ENGINE)

        # Send the summary using the provided callback function
        await send_reply_func(summary)
    except Exception as e:
        # Log any errors
        logger.error(f"Error generating summary: {e}")
        await send_reply_func("Error in generating summary.")
