import json
import os

MEMU_DATA_DIR = os.path.join(os.environ.get('APPDATA', ''), 'memu-bot')
MESSAGES_FILE = os.path.join(MEMU_DATA_DIR, 'telegram-data', 'messages.json')

def get_recent_context(limit=10):
    """Reads the recent chat history from memU bot's data to provide context."""
    if not os.path.exists(MESSAGES_FILE):
        return ""
    
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            messages = json.load(f)
            
        recent = messages[-limit:]
        context_str = "Recent Context from memU Memory:\n"
        for msg in recent:
            role = "User" if not msg.get('isFromBot') else "memU"
            text = msg.get('text', '')
            context_str += f"{role}: {text}\n"
        return context_str
    except Exception as e:
        print(f"Error reading memU context: {e}")
        return ""

if __name__ == '__main__':
    print(get_recent_context())
