# AI-Powered Telegram Notion Bot

A smart Telegram bot that manages your Notion task database using natural language. Built with Python, Google Gemini AI, and the Notion API.

## Features

- **Natural Language Control**: "Add a task to buy groceries tomorrow", "Update task 12 status to Done".
- **AI-Powered Parsing**: Uses Google Gemini to intelligently extract task details (Title, Priority, Date, etc.).
- **Interactive UI**: Telegram buttons for quick actions (Done, Delete, Snooze).

## Prerequisites

1.  **Telegram Bot Token**: Get one from [@BotFather](https://t.me/BotFather).
2.  **Google Gemini API Key**: Get one from [Google AI Studio](https://aistudio.google.com/).
3.  **Notion Integration**:
    - Go to [Notion Developers](https://www.notion.so/my-integrations) and create an integration.
    - Copy the `Internal Integration Secret` (Key).
    - **Share** your Task Database with this integration connection.

## Notion Database Setup

For the bot to work, your Notion database must have the following properties:

| Property Name | Type | Options / Details |
| :--- | :--- | :--- |
| **Name** | Title | The main task name. |
| **Status** | Select | `Pending`, `In Progress`, `Done` |
| **Priority** | Select | `Low`, `Medium`, `High` |
| **Due Date** | Date | Standard date field. |
| **ID** | **Unique ID** | Prefix: anything (e.g., `TASK`), Start: `1`. |
| **Description** | Text | (Optional) Rich text for details. |

> **Note**: The "ID" property is crucial for the bot's precise update/delete features. You must add a property of type "Unique ID" and name it "ID".

## Installation

### Method 1: Docker (Recommended)

1.  Clone the repository:
    ```bash
    git clone https://github.com/yourusername/telegram-notion-bot.git
    cd telegram-notion-bot
    ```

2.  Create a `.env` file from the example (or just create it):
    ```env
    TELEGRAM_TOKEN=your_telegram_bot_token
    NOTION_KEY=your_notion_integration_key
    DATABASE_ID=your_notion_database_id
    GEMINI_KEY=your_google_gemini_key
    TELEGRAM_USERID=your_telegram_user_id
    ```
    *Tip: `TELEGRAM_USERID` restricts the bot to only reply to you.*

3.  Run with Docker Compose:
    ```bash
    docker-compose up --build -d
    ```

### Method 2: Local Python

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Run the bot:
    ```bash
    python -m src.main
    ```

## Usage

Start a chat with your bot and try these commands:

- **Create**: "Remind me to call John on Friday priority high"
- **Read**: "Show my pending tasks" or just "tasks"
- **Update**:
    - "Update task 15 status to Done"
    - "Set priority of 'Buy Milk' to High"
- **Delete**: "Delete task 20"

## Project Structure

```text
src/
├── bot/            # Telegram handlers & keyboards
├── services/       # Notion & AI logic
├── utils/          # Logging & Formatters
├── config.py       # Config validation
└── main.py         # Entry point
```

## License

MIT License. See [LICENSE](LICENSE) for details.
