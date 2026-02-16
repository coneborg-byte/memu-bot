import datetime
import os
import requests
import json
import logging
import sys
import psutil
import atexit
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler

import html
# Import the new bridges
import gmail_bridge
import yahoo_bridge

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("MODEL_NAME", "llama3.1:8b")

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

PID_FILE = "morpheus_bot.pid"

def check_singleton():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            try:
                old_pid = int(f.read().strip())
                if psutil.pid_exists(old_pid):
                    print(f"Conflict: Bot is already running (PID {old_pid}).")
                    sys.exit(1)
            except ValueError:
                pass # Corrupt PID file, proceed to overwrite

    # Write current PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! I am Morpheus, your local assistant. "
        "I can monitor all your linked Google accounts! Try /inbox, /summarize, /calendar, or /link."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Morpheus Commands:\n"
        "/start - Greeting\n"
        "/help - This message\n"
        "/inbox - Show latest emails from all accounts\n"
        "/summarize - Private summary of all inboxes (Local AI)\n"
        "/calendar - Show upcoming events from all accounts\n"
        "/link <name> - Link a new Google account (e.g. /link work)\n"
        "/accounts - List all linked accounts\n"
        "Just send text to chat with me normally."
    )
    await update.message.reply_text(help_text)

async def link_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the OAuth flow for a new Gmail account."""
    if not context.args:
        await update.message.reply_text("Usage: /link <account_name> (e.g., /link work)")
        return
    
    account_name = context.args[0]
    await update.message.reply_text(f"🔗 Starting Gmail link process for '{account_name}'... Check the host machine for the browser window.")
    
    try:
        # This will trigger the flow and save the token
        gmail_bridge.get_google_service('gmail', 'v1', account_name)
        await update.message.reply_text(f"✅ Gmail account '{account_name}' linked successfully!")
    except Exception as e:
        logging.error(f"Error linking account: {e}")
        await update.message.reply_text(f"❌ Failed to link Gmail account '{account_name}'.")

async def link_yahoo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Links a new Yahoo account using email and app password."""
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /link_yahoo <account_name> <email> <app_password>")
        return
    
    name, email_addr, password = context.args[0], context.args[1], context.args[2]
    # Join password if it contains spaces (typical for Yahoo app passwords)
    if len(context.args) > 3:
        password = "".join(context.args[2:])
        
    await update.message.reply_text(f"🔗 Linking Yahoo account '{name}'...")
    
    try:
        yahoo_bridge.save_yahoo_auth(name, email_addr, password)
        # Test connection
        emails = yahoo_bridge.fetch_recent_emails(name, 1)
        # If fetch_recent_emails succeeded, it returns a list (possibly empty)
        await update.message.reply_text(f"✅ Yahoo account '{name}' linked successfully!")
    except Exception as e:
        logging.error(f"Error linking Yahoo: {e}")
        await update.message.reply_text(f"❌ Failed to link Yahoo account '{name}'. Check your app password.")

async def list_linked_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all linked accounts."""
    gmail_accounts = gmail_bridge.list_accounts()
    yahoo_accounts = yahoo_bridge.list_yahoo_accounts()
    
    if not gmail_accounts and not yahoo_accounts:
        await update.message.reply_text("No accounts linked yet. Use /link or /link_yahoo to add one.")
        return
    
    text = "🔗 <b>Linked Accounts:</b>\n"
    if gmail_accounts:
        text += "\n<b>Gmail:</b>\n" + "\n".join([f"• {html.escape(a)}" for a in gmail_accounts])
    if yahoo_accounts:
        text += "\n<b>Yahoo:</b>\n" + "\n".join([f"• {html.escape(a)}" for a in yahoo_accounts])
        
    await update.message.reply_text(text, parse_mode="HTML")

async def inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists recent emails from ALL accounts (Gmail + Yahoo)."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    g_accounts = gmail_bridge.list_accounts()
    y_accounts = yahoo_bridge.list_yahoo_accounts()
    
    if not g_accounts and not y_accounts:
        await update.message.reply_text("No accounts linked. Use /link or /link_yahoo.")
        return

    full_text = "📬 <b>Aggregated Inbox:</b>\n\n"
    
    # Gmail
    for acc in g_accounts:
        try:
            emails = gmail_bridge.fetch_recent_emails(acc, 3)
            full_text += f"🔹 <b>Gmail: {html.escape(acc)}</b>\n"
            if emails:
                for i, e in enumerate(emails):
                    safe_subject = html.escape(e['subject'])
                    safe_from = html.escape(e['from'])
                    full_text += f"{i+1}. {safe_subject} (From: {safe_from})\n"
            else:
                full_text += "<i>No recent emails.</i>\n"
            full_text += "\n"
        except Exception as e:
            logging.error(f"Error fetching Gmail for {acc}: {e}")
            full_text += f"⚠️ <b>Gmail: {html.escape(acc)}</b> (Error fetching)\n\n"
            
    # Yahoo
    for acc in y_accounts:
        try:
            emails = yahoo_bridge.fetch_recent_emails(acc, 3)
            # Remove 'yahoo_' prefix from display name if it exists (for prettier output)
            display_name = acc.replace("yahoo_", "")
            full_text += f"🟣 <b>Yahoo: {html.escape(display_name)}</b>\n"
            if emails:
                for i, e in enumerate(emails):
                    safe_subject = html.escape(e['subject'])
                    safe_from = html.escape(e['from'])
                    full_text += f"{i+1}. {safe_subject} (From: {safe_from})\n"
            else:
                full_text += "<i>No recent emails.</i>\n"
            full_text += "\n"
        except Exception as e:
            logging.error(f"Error fetching Yahoo for {acc}: {e}")
            full_text += f"⚠️ <b>Yahoo: {html.escape(acc)}</b> (Error fetching)\n\n"
    
    await update.message.reply_text(full_text, parse_mode="HTML")

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists upcoming events from ALL accounts."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    accounts = gmail_bridge.list_accounts()
    
    if not accounts:
        await update.message.reply_text("No accounts linked. Use /link.")
        return

    full_text = "🗓️ <b>Aggregated Calendar:</b>\n\n"
    all_events = []
    for acc in accounts:
        events = gmail_bridge.fetch_upcoming_events(acc, 5)
        all_events.extend(events)
    
    # Sort all events by start time
    all_events.sort(key=lambda x: x['start'])
    
    for i, e in enumerate(all_events[:10]): # Show top 10 total
        start_str = e['start']
        if 'T' in start_str:
            dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
            start_str = dt.strftime('%b %d, %H:%M')
        
        safe_summary = html.escape(e['summary'])
        safe_acc = html.escape(e['account'])
        full_text += f"{i+1}. <b>{safe_summary}</b> ({safe_acc})\n   When: {start_str}\n\n"
    
    await update.message.reply_text(full_text, parse_mode="HTML")

async def summarize_emails(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Summarizes emails from ALL accounts using Ollama."""
    await update.message.reply_text("🔍 Aggregating and analyzing all inboxes... Local & Private.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    accounts = gmail_bridge.list_accounts()
    all_email_texts = []
    
    for acc in accounts:
        try:
            emails = gmail_bridge.fetch_recent_emails(acc, 3)
            for e in emails:
                all_email_texts.append(f"Source: Gmail ({acc})\nSubject: {e['subject']}\nFrom: {e['from']}\nContent: {e['snippet']}")
        except Exception as e:
            logging.error(f"Error summarizing Gmail for {acc}: {e}")
            
    y_accounts = yahoo_bridge.list_yahoo_accounts()
    for acc in y_accounts:
        try:
            emails = yahoo_bridge.fetch_recent_emails(acc, 3)
            for e in emails:
                all_email_texts.append(f"Source: Yahoo ({acc})\nSubject: {e['subject']}\nFrom: {e['from']}\nContent: {e['snippet']}")
        except Exception as e:
            logging.error(f"Error summarizing Yahoo for {acc}: {e}")
    
    if not all_email_texts:
        await update.message.reply_text("No emails found to summarize.")
        return

    combined_content = "\n\n---\n\n".join(all_email_texts)
    prompt = (
        "You are Morpheus, a private AI assistant. Below are snippets from several of the user's Google accounts. "
        "Provide a concise, bulleted summary of the most important things the user needs to know across ALL accounts. "
        "Mention which account the information came from if relevant. Highlight urgent tasks.\n\n"
        f"{combined_content}\n\n"
        "Summary:"
    )

    try:
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        summary = response.json().get("response", "I couldn't generate a summary.")
        await update.message.reply_text(f"📊 **Global Summary:**\n\n{summary}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Error summarizing: {e}")
        await update.message.reply_text("❌ Local AI processing failed.")

async def send_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a location on Telegram."""
    if len(context.args) < 2:
        # Default to the coordinates provided by the user if none specified
        lat, lon = 37.7749, -122.4194
    else:
        try:
            lat = float(context.args[0])
            lon = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Usage: /location <latitude> <longitude>")
            return
            
    await context.bot.send_location(chat_id=update.effective_chat.id, latitude=lat, longitude=lon)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward the user message to Ollama and return the response."""
    user_text = update.message.text
    if not user_text: return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        payload = {"model": MODEL, "prompt": user_text, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        ai_response = response.json().get("response", "I'm sorry, I couldn't generate a response.")
        await update.message.reply_text(ai_response)
    except Exception as e:
        logging.error(f"Ollama error: {e}")
        await update.message.reply_text("❌ Error: Ollama is unreachable.")

if __name__ == '__main__':
    check_singleton()
    atexit.register(cleanup_pid)
    if not TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('inbox', inbox))
    application.add_handler(CommandHandler('summarize', summarize_emails))
    application.add_handler(CommandHandler('calendar', calendar))
    application.add_handler(CommandHandler('location', send_location))
    application.add_handler(CommandHandler('link', link_account))
    application.add_handler(CommandHandler('link_yahoo', link_yahoo))
    application.add_handler(CommandHandler('accounts', list_linked_accounts))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Morpheus Bot (Multi-Account) is starting...")
    application.run_polling()
