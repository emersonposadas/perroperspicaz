"""
This module contains functionalities for fetching news using Bing News API 
and summarizing the news articles using OpenAI's GPT-4 model. 
It uses environment variables for configuration and provides async functions 
for news fetching and summarization.
"""
import os
import logging
import requests
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
    """
    Fetches news articles from the Bing News API based on the given query.
    
    Args:
        query (str): The search query for fetching news articles.

    Returns:
        list: A list of news articles, each containing details like name and description.
    """
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
        logger.error("Error fetching news: %s", e)
        return []

async def summarize_with_gpt4(articles, send_reply_func):
    """
    Asynchronously summarizes a list of articles using OpenAI's GPT-4 model.

    Args:
        articles (list): A list of news articles to summarize.
        send_reply_func (async function): An async callback function to send the summary.

    This function combines article titles and descriptions, generates a summary using GPT-4,
    and sends the summary through the provided callback function.
    """
    # Combine the titles and descriptions of all articles into one text
    combined_text = ' '.join(
        [f"{article['name']}. {article['description']}" for article in articles]
    )

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
        summary = (
            response.choices[0].text.strip()
            if response.choices else "No clear summary available."
        )

        # Log the summary generation
        logger.info("Generated summary using %s.", PP_OPENAI_ENGINE)

        # Format the message with summary and inline links
        source_links = ', '.join(
            [f"[{idx + 1}]({article['url']})" for idx, article in enumerate(articles)]
        )
        message_with_links = summary + "\n\nSources: " + source_links

        # Send the formatted message using the provided callback function
        await send_reply_func(message_with_links)
    except Exception as e:
        # Log any errors
        logger.error("Error generating summary: %s", e)
        await send_reply_func("Error in generating summary.")
