# PerroPerspicaz Bot

## Introduction
PerroPerspicaz is a versatile Telegram bot integrating multiple features including news retrieval, YouTube playlist management, and interaction with OpenAI's GPT model for text analysis and response generation.

## Features
- **News Retrieval**: Fetches news articles based on user queries using the NewsAPI.
- **YouTube Playlist Management**: Adds songs to a specified YouTube playlist and recommends random songs from the playlist.
- **OpenAI Integration**: Utilizes OpenAI's GPT model to generate responses and analyze texts for logical fallacies.
- **Telegram Bot Interaction**: Handles user commands and messages within Telegram.

## Installation
To install and run PerroPerspicaz, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/perroperspicaz/perroperspicaz.git
   ```
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Set up the required environment variables in a `.env` file:
- `PP_TELEGRAM_TOKEN`: Your Telegram Bot Token.
- `PP_OPENAI_TOKEN`: Your OpenAI API key.
- `PP_NEWSAPI_KEY`: Your NewsAPI key.
- Other optional configurations as needed.

## Usage
1. Start the bot using:
   ```python
   python main.py
   ```
2. Interact with the bot on Telegram using supported commands like `/news`, `/addsong`, `/getsong`, etc.

## Dependencies
- Python 3.8+
- Libraries: `python-telegram-bot`, `google-api-python-client`, `newsapi-python`, `openai`, etc.

## Contributing
Contributions to the PerroPerspicaz bot are welcome. 

## License

This project is dual-licensed:

- **Open Source License**: The software is available under the MIT License for open-source use. Under this license, you are free to use, modify, and distribute the software, provided that credit is given to the original author.

- **Commercial License**: For commercial use, a separate commercial license is available. This license is tailored for businesses and commercial entities who wish to utilize the software in a commercial capacity. It includes additional features and support not available in the open-source version.

For more information, please contact the author.

