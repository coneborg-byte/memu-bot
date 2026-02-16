# memU Bot (Sovereign AI Assistant) 🤖🦾

memU bot is a privacy-first, local-AI powered assistant that aggregates your Gmail and Yahoo Mail inboxes and calendars into a single Telegram interface. It uses a local Ollama instance for all AI processing, ensuring your sensitive data never leaves your workstation.

## 🌟 Features
- **Aggregated Inboxes**: View recent emails from multiple Gmail and Yahoo accounts in one place.
- **Private Summaries**: Uses local AI (Ollama) to summarize your inboxes securely.
- **Calendar Integration**: Consolidated view of upcoming events across all linked Google accounts.
- **Location Skill**: Share geographical coordinates easily.
- **Singleton Pattern**: Robust process management to prevent multiple bot instances.

## 🛠️ Tech Stack
- **Python**: Core logic and bot framework.
- **python-telegram-bot**: Telegram API integration.
- **Ollama**: Local AI model hosting (defaulting to `llama3.1:8b`).
- **Google APIs**: Gmail and Calendar integration.
- **IMAP**: Secure Yahoo Mail access using App Passwords.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) installed and running locally.
- A Telegram bot token from [@BotFather](https://t.me/botfather).

### 2. Installation
```bash
git clone https://github.com/yourusername/memu-bot.git
cd memu-bot
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in your details:
```bash
cp .env.example .env
```

### 4. Linking Accounts
- **Gmail**: Run `/link <account_name>` in the bot. It will open a browser window for OAuth.
- **Yahoo**: Run `/link_yahoo <account_name> <email> <app_password>` in the bot.

## 💬 Usage
- `/inbox`: View aggregated inbox.
- `/summarize`: Generate a private AI summary of your emails.
- `/calendar`: View upcoming events.
- `/location`: Send default or custom coordinates.
- `/accounts`: List all linked accounts.

## 🛡️ Privacy & Security
- **Local AI**: All summarization and chat processing happens locally via Ollama.
- **Isolated Tokens**: Account credentials and tokens are stored in the `tokens/` directory (excluded from Git).
- **App Passwords**: Secure access to Yahoo Mail without sharing your main password.
