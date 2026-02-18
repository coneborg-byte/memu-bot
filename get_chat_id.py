import requests, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
resp = requests.get(f'https://api.telegram.org/bot{token}/getUpdates')
updates = resp.json().get('result', [])
if updates:
    for u in updates[-5:]:
        msg = u.get('message') or u.get('channel_post') or {}
        chat = msg.get('chat', {})
        print(f"Chat ID: {chat.get('id')} | Type: {chat.get('type')} | Name: {chat.get('first_name','') or chat.get('title','')}")
else:
    print('No updates found - send a message to the bot first')
