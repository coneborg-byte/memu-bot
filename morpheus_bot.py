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
import gmail_bridge
import yahoo_bridge
import memu_bridge

MISSION_DIR = "missions"
if not os.path.exists(MISSION_DIR):
    os.makedirs(MISSION_DIR)

def log_mission(action, data):
    """Writes a mission packet to the missions/ folder for Antigravity to process."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mission_id = f"mission_{timestamp}_{action}.json"
    filepath = os.path.join(MISSION_DIR, mission_id)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"action": action, "data": data, "status": "pending", "timestamp": timestamp}, f, indent=2)
    return mission_id

# Load environment variables
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
MODEL = os.getenv("MODEL_NAME", "llama3.1:8b")
MEMU_API_KEY = os.getenv("MEMU_API_KEY")

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
        "🤖 Morpheus: Executive Router (Digital Nervous System)\n\n"
        "Commands:\n"
        "/start - System status\n"
        "/help - This overview\n"
        "/inbox - Show aggregated inboxes (Gmail/Yahoo)\n"
        "/summarize - Private summary (Powered by memU context)\n"
        "/briefing - Presidential Daily Briefing (Emails, Calendar, Drive, CRM)\n"
        "/crm - View/Search your Local CRM Contact Profiles\n"
        "/research - Search your local research Library\n"
        "/scout - Scan X (Twitter) for latest Alpha/Intel\n"
        "/consult - Convene the Business Advisory Council\n"
        "/secure - Run an automated Security Council code audit\n"
        "/calendar - Upcoming events\n"
        "/drive - Recent Google Drive files\n"
        "/memory - Check what I've learned from memU\n"
        "/delete_alerts - Delete security alerts (Gmail/Yahoo)\n"
        "/link <name> - Link Gmail account\n"
        "/accounts - List all connections\n\n"
        "Just chat to route tasks through me."
    )
    await update.message.reply_text(help_text)
    
async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the recent context retrieved from memU memory."""
    mem_context = memu_bridge.get_recent_context(5)
    if mem_context:
        await update.message.reply_text(f"🧠 <b>Morpheus Internal Memory (via memU):</b>\n\n{mem_context}", parse_mode="HTML")
    else:
        await update.message.reply_text("📭 My memory from memU is currently empty or unreachable.")


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

async def drive_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists recent files from Google Drive from ALL accounts."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    accounts = gmail_bridge.list_accounts()
    
    if not accounts:
        await update.message.reply_text("No Google accounts linked. Use /link.")
        return

    full_text = "📂 <b>Recent Google Drive Files:</b>\n\n"
    for acc in accounts:
        try:
            files = gmail_bridge.fetch_recent_files(acc, 5)
            full_text += f"🔹 <b>Account: {html.escape(acc)}</b>\n"
            if files:
                for i, f in enumerate(files):
                    safe_name = html.escape(f['name'])
                    modified_dt = datetime.datetime.fromisoformat(f['modified'].replace('Z', '+00:00'))
                    mod_str = modified_dt.strftime('%b %d, %H:%M')
                    full_text += f"{i+1}. {safe_name} (Modified: {mod_str})\n"
            else:
                full_text += "<i>No recent files.</i>\n"
            full_text += "\n"
        except Exception as e:
            logging.error(f"Error fetching Drive for {acc}: {e}")
            full_text += f"⚠️ <b>Account: {html.escape(acc)}</b> (Error fetching)\n\n"
    
    await update.message.reply_text(full_text, parse_mode="HTML")

async def delete_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deletes 'Security alert' emails from all linked accounts."""
    await update.message.reply_text("🧹 Searching for security alerts to delete...")
    
    g_accounts = gmail_bridge.list_accounts()
    y_accounts = yahoo_bridge.list_yahoo_accounts()
    
    deleted_count = 0
    
    # Process Gmail
    for acc in g_accounts:
        try:
            emails = gmail_bridge.fetch_recent_emails(acc, 20)
            for e in emails:
                if "Security alert" in e['subject']:
                    if gmail_bridge.delete_email(acc, e['id']):
                        deleted_count += 1
        except Exception as e:
            logging.error(f"Error deleting Gmail alerts for {acc}: {e}")
                    
    # Process Yahoo
    for acc in y_accounts:
        try:
            emails = yahoo_bridge.fetch_recent_emails(acc, 20)
            for e in emails:
                if "Security alert" in e['subject']:
                    if yahoo_bridge.delete_email(acc, e['id']):
                        deleted_count += 1
        except Exception as e:
            logging.error(f"Error deleting Yahoo alerts for {acc}: {e}")
                    
    if deleted_count > 0:
        await update.message.reply_text(f"✅ Success! Deleted {deleted_count} security alert emails.")
    else:
        await update.message.reply_text("📭 No security alert emails were found.")

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
    
    # Add Drive Files
    for acc in accounts:
        try:
            files = gmail_bridge.fetch_recent_files(acc, 3)
            for f in files:
                all_email_texts.append(f"Source: Google Drive ({acc})\nFile: {f['name']}\nType: {f['type']}\nModified: {f['modified']}")
        except Exception as e:
            logging.error(f"Error summarizing Drive for {acc}: {e}")
    
    if not all_email_texts:
        await update.message.reply_text("No emails found to summarize.")
        return

    combined_content = "\n\n---\n\n".join(all_email_texts)
    mem_context = memu_bridge.get_recent_context(5)
    
    prompt = (
        "You are Morpheus, the Executive Router of a Digital Nervous System. "
        "Your role is to summarize information and direct actions. "
        f"\n\n{mem_context}\n\n"
        "Below are snippets from the user's accounts. "
        "Provide a concise summary, highlighting urgent tasks or items that match the user's known preferences from the context above.\n\n"
        f"{combined_content}\n"
        "\nSummary:"
    )

    try:
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        summary = response.json().get("response", "I couldn't generate a summary.")
        await update.message.reply_text(f"📊 Global Summary:\n\n{summary}")
    except Exception as e:
        logging.error(f"Error summarizing: {e}")
        await update.message.reply_text("❌ Local AI processing failed.")

async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a Presidential Daily Briefing."""
    await update.message.reply_text("📋 Preparing your Presidential Daily Briefing... Scanning Nervous System.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    g_accounts = gmail_bridge.list_accounts()
    y_accounts = yahoo_bridge.list_yahoo_accounts()
    
    brief_data = []
    
    # 1. Emails
    brief_data.append("--- RECENT COMMUNICATIONS ---")
    for acc in g_accounts:
        emails = gmail_bridge.fetch_recent_emails(acc, 2)
        for e in emails:
            brief_data.append(f"GMAIL ({acc}): From {e['from']} | Sub: {e['subject']}")
            
    for acc in y_accounts:
        emails = yahoo_bridge.fetch_recent_emails(acc, 2)
        for e in emails:
            brief_data.append(f"YAHOO ({acc}): From {e['from']} | Sub: {e['subject']}")

    # 2. Calendar
    brief_data.append("\n--- UPCOMING SCHEDULE ---")
    for acc in g_accounts:
        events = gmail_bridge.fetch_upcoming_events(acc, 5)
        for ev in events:
            brief_data.append(f"CALENDAR ({acc}): {ev['start']} - {ev['summary']}")

    # 3. Drive
    brief_data.append("\n--- RECENT INTEL (FILES) ---")
    for acc in g_accounts:
        files = gmail_bridge.fetch_recent_files(acc, 3)
        for f in files:
            brief_data.append(f"DRIVE ({acc}): {f['name']} (Mod: {f['modified']})")

    # 4. CRM (Relationship Nudges)
    crm_data = ""
    if os.path.exists("CONTACTS.md"):
        with open("CONTACTS.md", "r", encoding="utf-8") as f:
            crm_data = f.read()

    combined_brief = "\n".join(brief_data)
    mem_context = memu_bridge.get_recent_context(10)
    
    if os.path.exists("IDENTITY.md"):
        with open("IDENTITY.md", "r", encoding="utf-8") as f:
            identity = f.read()
    else:
        identity = "You are Morpheus, the Executive Router."

    prompt = (
        f"{identity}\n\n"
        "TASK: Provide a high-level Presidential Daily Briefing. "
        "Highlight exactly what the user needs to focus on in Wales today. "
        "Include 'Relationship Nudges' based on the CRM data below if appropriate.\n"
        "Be concise, efficient, and professional. Use emojis.\n\n"
        f"MEMU MEMORY:\n{mem_context}\n\n"
        f"CRM DATA:\n{crm_data}\n\n"
        f"NERVOUS SYSTEM DATA:\n{combined_brief}\n"
        "\nMorpheus Daily Brief:"
    )

    try:
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        report = response.json().get("response", "Intelligence report failed.")
        await update.message.reply_text(f"⚔️ **DAILY INTELLIGENCE BRIEF** ⚔️\n\n{report}", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Briefing error: {e}")
        await update.message.reply_text("❌ Intelligence gathering failed at the source.")

async def crm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the local CRM profiles."""
    if os.path.exists("CONTACTS.md"):
        with open("CONTACTS.md", "r", encoding="utf-8") as f:
            content = f.read()
        await update.message.reply_text(f"👥 **Local CRM Profiles:**\n\n{content}")
    else:
        await update.message.reply_text("📭 CRM is empty. Try 'Morpheus, add Sarah to my contacts'.")

async def send_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a location on Telegram."""
    if len(context.args) < 2:
        lat, lon = 37.7749, -122.4194
    else:
        try:
            lat = float(context.args[0])
            lon = float(context.args[1])
        except ValueError:
            await update.message.reply_text("Usage: /location <latitude> <longitude>")
            return
    await context.bot.send_location(chat_id=update.effective_chat.id, latitude=lat, longitude=lon)

async def research_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches the local knowledge library."""
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("🔍 Please provide a topic, e.g. /research Forex rates")
        return

    await update.message.reply_text(f"📚 Searching Library for: {query}...")
    
    library_path = "library"
    findings = []
    
    if os.path.exists(library_path):
        for filename in os.listdir(library_path):
            if filename.endswith(".md") or filename.endswith(".txt"):
                try:
                    with open(os.path.join(library_path, filename), "r", encoding="utf-8") as f:
                        content = f.read()
                        if query.lower() in content.lower():
                            findings.append(f"📄 **{filename}**\n{content[:300]}...")
                except Exception as e:
                    logging.error(f"Error reading {filename}: {e}")

    if not findings:
        await update.message.reply_text("📭 No matching documents found in the library.")
    else:
        await update.message.reply_text("\n\n---\n\n".join(findings[:3]))

async def scout_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initiates an X (Twitter) scouting mission."""
    topic = " ".join(context.args)
    if not topic:
        await update.message.reply_text("📡 Please specify a topic, e.g. /scout AI News")
        return

    await update.message.reply_text(f"🦾 **Scout Mission Initiated.**\n\nI have alerted Antigravity to scan X for latest Alpha on: **{topic}**.\nCheck back shortly for the Library update.")
    log_mission("scout_x", {"topic": topic})
    logging.info(f"SCOUT MISSION: {topic}")

async def consult_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convenes the Business Advisory Council for a problem."""
    problem = " ".join(context.args)
    if not problem:
        await update.message.reply_text("🏛️ Please provide a problem for the Council to review, e.g. /consult Should I upgrade my RAM?")
        return

    await update.message.reply_text("🎭 Convening the Business Advisory Council... Gathering perspectives.")
    
    council_path = "COUNCILS"
    advisors = {}
    if os.path.exists(council_path):
        for f in os.listdir(council_path):
            if f.endswith(".md"):
                with open(os.path.join(council_path, f), "r", encoding="utf-8") as file:
                    advisors[f.replace(".md", "")] = file.read()

    prompt = (
        "You are Morpheus, chairing the Business Advisory Council. "
        f"The user has posed the following problem: '{problem}'\n\n"
        "You must provide a response that incorporates the following advisor perspectives:\n"
        f"{json.dumps(advisors, indent=2)}\n\n"
        "Present the answer as a structured 'Council Report' with a section for each advisor and a final chairperson conclusion."
    )

    try:
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        report = response.json().get("response", "Council failed to reach a quorum.")
        await update.message.reply_text(f"🏛️ **COUNCIL MEETING MINUTES** 🏛️\n\n{report}")
    except Exception as e:
        logging.error(f"Council error: {e}")
        await update.message.reply_text("❌ The Council has encountered a logical deadlock.")

async def security_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convenes the Security Council to perform a codebase audit."""
    await update.message.reply_text("🛡️ **Security Council is assembling.** Reading current codebase for vulnerabilities...")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # 1. Load Security Personas
    council_path = "SECURITY_COUNCIL"
    advisors = {}
    if os.path.exists(council_path):
        for f in os.listdir(council_path):
            if f.endswith(".md"):
                with open(os.path.join(council_path, f), "r", encoding="utf-8") as file:
                    advisors[f.replace(".md", "")] = file.read()

    # 2. Ingest Codebase (only .py and .md, sanitize .env)
    code_intel = []
    files_to_scan = ['morpheus_bot.py', 'gmail_bridge.py', 'yahoo_bridge.py', 'memu_bridge.py', '.env']
    for filename in files_to_scan:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                if filename == '.env':
                    # Redact secrets for the AI
                    content = "REDRESSED .ENV (Secrets hidden)"
                code_intel.append(f"FILE: {filename}\n{content[:2000]}") # Limit per file for token safety

    combined_code = "\n\n---\n\n".join(code_intel)

    prompt = (
        "You are chairing the MORPHEUS SECURITY COUNCIL. "
        "Analyze the following codebase from four perspectives: Offensive, Defensive, Privacy, and Operational Realism.\n\n"
        f"ADVISOR PERSONAS:\n{json.dumps(advisors, indent=2)}\n\n"
        f"CODEBASE TO AUDIT:\n{combined_code}\n\n"
        "Provide a structured Security Report with numbered vulnerabilities and specific recommendations. "
        "Highlight ANY critical risks immediately."
    )

    try:
        payload = {"model": MODEL, "prompt": prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=180) # Longer timeout for audit
        report = response.json().get("response", "Security audit timed out.")
        log_mission("security_audit", {"report_summary": report[:500]})
        await update.message.reply_text(f"⚔️ **SECURITY COUNCIL AUDIT REPORT** ⚔️\n\n{report}")
    except Exception as e:
        logging.error(f"Security Board error: {e}")
        await update.message.reply_text("❌ The Security Council was disrupted during the audit.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward the user message to Ollama and return the response."""
    user_text = update.message.text
    if not user_text: return
    
    logging.info(f"--- Incoming Message from {update.effective_user.first_name} ---")
    logging.info(f"Text: {user_text}")

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    mem_context = memu_bridge.get_recent_context(10)
    
    if MEMU_API_KEY and MEMU_API_KEY != "YOUR_MU_KEY_HERE":
        # Strategy: Use the API key to enrich the context if valid
        # For now, we store the key for future API-based context retrieval
        pass

    mem_context = memu_bridge.get_recent_context(10)

    try:
        # Stage 1: Intent Detection
        intent_prompt = (
            "You are the Brain of Morpheus. Distill the user's intent into a JSON action if they want to perform a task. "
            "Available Actions:\n"
            "- {'action': 'remember_fact', 'fact': '<val>'}\n"
            "- {'action': 'update_contact', 'name': '<name>', 'note': '<note>'}\n"
            "- {'action': 'save_research', 'title': '<title>', 'content': '<full_content>'}\n"
            "- {'action': 'scout_x', 'topic': 'Llama 4 news'}\n"
            "- {'action': 'none'}\n\n"
            f"User Message: {user_text}\n"
            "Respond ONLY with the JSON: "
        )
        
        intent_payload = {"model": MODEL, "prompt": intent_prompt, "stream": False, "format": "json"}
        intent_resp = requests.post(OLLAMA_URL, json=intent_payload, timeout=30)
        intent_data = intent_resp.json().get("response", "{}")
        
        try:
            action_json = json.loads(intent_data)
        except:
            action_json = {"action": "none"}

        status_msg = ""
        if action_json.get("action") == "delete_emails":
            query = action_json.get("query", "")
            await update.message.reply_text(f"🦾 Understanding intent: Deleting emails matching '{query}'...")
            
            g_accounts = gmail_bridge.list_accounts()
            y_accounts = yahoo_bridge.list_yahoo_accounts()
            deleted = 0
            
            # Map 'sender' query to 'from' key used in bridge data
            search_key = "from" if "sender" in query.lower() else "subject"
            val = query.split(":", 1)[1] if ":" in query else query
            
            for acc in g_accounts:
                try:
                    emails = gmail_bridge.fetch_recent_emails(acc, 30)
                    for e in emails:
                        if val.lower() in e[search_key].lower():
                            if gmail_bridge.delete_email(acc, e['id']): deleted += 1
                except Exception as ex:
                    logging.error(f"Gmail delete inner error: {ex}")
            
            for acc in y_accounts:
                try:
                    emails = yahoo_bridge.fetch_recent_emails(acc, 30)
                    for e in emails:
                        if val.lower() in e[search_key].lower():
                            if yahoo_bridge.delete_email(acc, e['id']): deleted += 1
                except Exception as ex:
                    logging.error(f"Yahoo delete inner error: {ex}")
            
            status_msg = f"\n\n(Action Report: I successfully deleted {deleted} emails matching your request.)"

        elif action_json.get("action") == "remember_fact":
            fact = action_json.get("fact", "")
            with open("KNOWLEDGE.md", "a", encoding="utf-8") as f:
                f.write(f"\n- {fact}")
            status_msg = f"\n\n(Memory Logged: I have added that to my permanent knowledge base.)"

        elif action_json.get("action") == "update_contact":
            name = action_json.get("name", "")
            note = action_json.get("note", "")
            # Simple append to MD for now
            with open("CONTACTS.md", "a", encoding="utf-8") as f:
                f.write(f"\n| **{name}** | Unknown | {datetime.datetime.now().strftime('%Y-%m-%d')} | {note} | Nudge TBD |")
            status_msg = f"\n\n(CRM Updated: Profile for {name} has been refreshed.)"

        elif action_json.get("action") == "save_research":
            title = action_json.get("title", "Research_" + datetime.datetime.now().strftime("%H%M%S"))
            content = action_json.get("content", "")
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).rstrip()
            filename = f"library/{safe_title.replace(' ', '_')}.md"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {title}\nDate: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n{content}")
            log_mission("save_research", {"title": title, "filepath": filename})
            status_msg = f"\n\n(Library Updated: '{title}' has been archived in the vaults.)"

        elif action_json.get("action") == "scout_x":
            topic = action_json.get("topic", "")
            log_mission("scout_x", {"topic": topic})
            status_msg = f"\n\n(Scout Alert: I have pinged Antigravity to run a deep scan of X for '{topic}'. Stand by for the data dump.)"

        # Stage 2: Conversational Response
        knowledge = ""
        if os.path.exists("KNOWLEDGE.md"):
            with open("KNOWLEDGE.md", "r", encoding="utf-8") as f:
                knowledge = f.read()

        if os.path.exists("IDENTITY.md"):
            with open("IDENTITY.md", "r", encoding="utf-8") as f:
                system_identity = f.read()
        else:
            system_identity = "You are Morpheus, the Executive Router."

        system_instructions = (
            f"{system_identity}\n\n"
            f"PERMANENT KNOWLEDGE:\n{knowledge}\n\n"
            "IMPORTANT: Antigravity IS a real, active application. memU IS providing memory. "
            f"Current memU Memory:\n{mem_context}\n"
        )
        full_prompt = f"{system_instructions}\nUser: {user_text}\nMorpheus: "
        
        payload = {"model": MODEL, "prompt": full_prompt, "stream": False}
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        ai_response = response.json().get("response", "")
        
        await update.message.reply_text(f"{ai_response}{status_msg}")
    except Exception as e:
        import traceback
        logging.error(f"Error in handle_message: {e}")
        logging.error(traceback.format_exc())
        await update.message.reply_text("❌ Morpheus encountered an internal error. Checking logical circuits...")

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
    application.add_handler(CommandHandler('briefing', briefing_command))
    application.add_handler(CommandHandler('crm', crm_command))
    application.add_handler(CommandHandler('research', research_command))
    application.add_handler(CommandHandler('scout', scout_command))
    application.add_handler(CommandHandler('consult', consult_command))
    application.add_handler(CommandHandler('secure', security_command))
    application.add_handler(CommandHandler('calendar', calendar))
    application.add_handler(CommandHandler('drive', drive_files))
    application.add_handler(CommandHandler('location', send_location))
    application.add_handler(CommandHandler('memory', memory_command))
    application.add_handler(CommandHandler('delete_alerts', delete_alerts))
    application.add_handler(CommandHandler('link', link_account))
    application.add_handler(CommandHandler('link_yahoo', link_yahoo))
    application.add_handler(CommandHandler('accounts', list_linked_accounts))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("Morpheus Bot (Multi-Account) is starting...")
    application.run_polling()
