import imaplib
import email
from email.header import decode_header
import os
import json
import glob

TOKEN_DIR = 'tokens'

def get_yahoo_auth(account_id):
    """Retrieves Yahoo credentials from local tokens directory."""
    token_path = os.path.join(TOKEN_DIR, f'yahoo_{account_id}.json')
    if os.path.exists(token_path):
        with open(token_path, 'r') as f:
            return json.load(f)
    return None

def save_yahoo_auth(account_id, email_addr, app_password):
    """Saves Yahoo credentials to local tokens directory."""
    if not os.path.exists(TOKEN_DIR):
        os.makedirs(TOKEN_DIR)
    token_path = os.path.join(TOKEN_DIR, f'yahoo_{account_id}.json')
    with open(token_path, 'w') as f:
        json.dump({'email': email_addr, 'password': app_password}, f)

def list_yahoo_accounts():
    """Lists all Yahoo account IDs that have a stored token."""
    if not os.path.exists(TOKEN_DIR):
        return []
    files = glob.glob(os.path.join(TOKEN_DIR, "yahoo_*.json"))
    return [os.path.basename(f).replace("yahoo_", "").replace(".json", "") for f in files]

def fetch_recent_emails(account_id, max_results=5):
    """Fetches recent emails from Yahoo inbox."""
    auth = get_yahoo_auth(account_id)
    if not auth:
        return []

    try:
        # Connect to Yahoo IMAP
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(auth['email'], auth['password'])
        mail.select("inbox")

        # Search for all emails in inbox
        status, messages = mail.search(None, "ALL")
        if status != 'OK':
            return []

        # Get the list of email IDs
        mail_ids = messages[0].split()
        # Fetch the last N emails
        recent_ids = mail_ids[-max_results:]
        recent_ids.reverse()

        email_data = []
        for m_id in recent_ids:
            status, msg_data = mail.fetch(m_id, "(RFC822)")
            if status != 'OK':
                continue

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject_header = msg.get("Subject")
                    if subject_header:
                        subject, encoding = decode_header(subject_header)[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8", errors="replace")
                    else:
                        subject = "No Subject"
                    
                    # Decode sender
                    from_header = msg.get("From")
                    if from_header:
                        sender, encoding = decode_header(from_header)[0]
                        if isinstance(sender, bytes):
                            sender = sender.decode(encoding if encoding else "utf-8", errors="replace")
                    else:
                        sender = "Unknown"

                    # Get snippet (first part of body)
                    snippet = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    snippet = part.get_payload(decode=True).decode(errors="replace")[:200]
                                    break
                                except Exception:
                                    pass
                    else:
                        try:
                            snippet = msg.get_payload(decode=True).decode(errors="replace")[:200]
                        except Exception:
                            pass

                    email_data.append({
                        'id': m_id.decode(),
                        'account': f"yahoo_{account_id}",
                        'subject': subject,
                        'from': sender,
                        'date': msg.get("Date"),
                        'snippet': snippet.strip().replace('\n', ' ')
                    })

        mail.logout()
        return email_data

    except Exception as e:
        print(f"Error fetching Yahoo emails for {account_id}: {e}")
        return []
