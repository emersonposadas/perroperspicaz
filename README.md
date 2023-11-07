# PerroPerspicaz Telegram Bot

PerroPerspicaz is a sophisticated Telegram bot designed to analyze text for logical fallacies using the OpenAI API. It offers a convenient way for users to get quick feedback on their text snippets directly within the Telegram chat interface.

## Features

- Respond to messages with a thinking emoji.
- Analyze text for logical fallacies.
- Quote the source message that contains the thinking emoji.

## Installation

Before you begin, make sure you have Python 3.11 installed on your system. If you do not have it installed, download and install it from [Python's official website](https://www.python.org/downloads/release/python-3110/).

To set up your instance of the PerroPerspicaz bot, follow these steps:

1. **Clone the repository**:

    ```bash
    git clone https://github.com/emersonposadas/perroperspicaz.git
    cd perroperspicaz
    ```

2. **Set up a virtual environment** (optional but recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate.bat`
    ```

3. **Install the dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

## Dependencies

Ensure you have the following dependencies installed with the exact versions as listed in the `requirements.txt` file:

```plaintext
aiofiles==23.1.0
aiogram==3.1.1
aiohttp==3.8.6
... (rest of the dependencies)
python-telegram-bot==20.6

