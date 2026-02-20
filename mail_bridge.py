import datetime
import os.path
import base64
import glob
import json
import imaplib
import email
from email.header import decode_header
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the token files.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.file'
]

# Handle absolute paths
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_DIR = os.path.join(ROOT_DIR, 'tokens', 'gmail')
YAHOO_TOKEN_DIR = os.path.join(ROOT_DIR, 'tokens', 'yahoo')
CREDENTIALS_FILE = os.path.join(ROOT_DIR, 'credentials.json')

# --- GMAIL / GOOGLE LOGIC ---

def get_google_service(service_name, version, account_id='primary'):
    """Builds and returns the requested Google service object for a specific account."""
    if not os.path.exists(TOKEN_DIR):
        os.makedirs(TOKEN_DIR)
        
    token_path = os.path.join(TOKEN_DIR, f'{account_id}.json')
    creds = None
    
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except ValueError:
            print(f"Error: Token file {token_path} is malformed. Deleting and re-linking.")
            os.remove(token_path)
            creds = None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        
        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: {CREDENTIALS_FILE} not found. Gmail linking will fail.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(service_name, version, credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def fetch_recent_gmail_emails(account_id='primary', max_results=5):
    """Fetches the last N emails from the Gmail inbox."""
    service = get_google_service('gmail', 'v1', account_id)
    if not service:
        return []

    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        email_data = []
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            
            payload = txt.get('payload', {})
            headers = payload.get('headers', [])
            subject = "No Subject"
            sender = "Unknown"
            date = "Unknown"
            
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']
                if header['name'] == 'Date':
                    date = header['value']

            snippet = txt.get('snippet', '')

            email_data.append({
                'id': msg['id'],
                'account': account_id,
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': snippet,
                'type': 'gmail'
            })
            
        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

# --- YAHOO / IMAP LOGIC ---

def fetch_recent_yahoo_emails(account_id, max_results=5):
    """Fetches the last N emails from the Yahoo inbox using IMAP."""
    token_path = os.path.join(YAHOO_TOKEN_DIR, f'{account_id}.json')
    if not os.path.exists(token_path):
        return []

    try:
        with open(token_path, 'r') as f:
            creds = json.load(f)
        
        email_addr = creds.get("email")
        password = creds.get("password")
        
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        mail.login(email_addr, password)
        mail.select("inbox")
        
        status, messages = mail.search(None, "ALL")
        if status != "OK":
            return []
            
        mail_ids = messages[0].split()
        # Last N messages (newest first)
        num_to_fetch = min(len(mail_ids), max_results)
        recent_ids = mail_ids[-num_to_fetch:][::-1]
        
        results = []
        for m_id in recent_ids:
            status, data = mail.fetch(m_id, "(RFC822)")
            if status != "OK":
                continue
            
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            # Decode Subject
            subject_header = msg.get("Subject", "No Subject")
            decoded_parts = decode_header(subject_header)
            subject = ""
            for out, enc in decoded_parts:
                if isinstance(out, bytes):
                    subject += out.decode(enc or 'utf-8', errors='ignore')
                else:
                    subject += out
            
            sender = msg.get("From", "Unknown")
            date = msg.get("Date", "Unknown")
            
            # Extract Snippet (plain text body)
            snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            snippet = payload.decode(errors='ignore')[:300]
                        break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    snippet = payload.decode(errors='ignore')[:300]
            
            results.append({
                'id': f"yahoo_{m_id.decode()}", # unique prefix
                'account': account_id,
                'subject': subject,
                'from': sender,
                'date': date,
                'snippet': snippet.replace("\r", " ").replace("\n", " ").strip(),
                'type': 'yahoo'
            })
        
        mail.logout()
        return results
    except Exception as e:
        print(f'Yahoo error for {account_id}: {e}')
        return []

# --- UNIFIED LOGIC ---

def list_all_accounts():
    """Lists all linked Gmail and Yahoo accounts."""
    accounts = []
    
    if os.path.exists(TOKEN_DIR):
        gmail_files = glob.glob(os.path.join(TOKEN_DIR, "*.json"))
        for f in gmail_files:
            accounts.append({
                'id': os.path.basename(f).replace(".json", ""),
                'type': 'gmail'
            })
            
    if os.path.exists(YAHOO_TOKEN_DIR):
        yahoo_files = glob.glob(os.path.join(YAHOO_TOKEN_DIR, "*.json"))
        for f in yahoo_files:
            accounts.append({
                'id': os.path.basename(f).replace(".json", ""),
                'type': 'yahoo'
            })
            
    return accounts

def fetch_recent_emails(account_id='primary', max_results=5):
    """Fetches emails from a specific account (autodetects type)."""
    # Check if it's a known Gmail account
    gmail_path = os.path.join(TOKEN_DIR, f"{account_id}.json")
    if os.path.exists(gmail_path):
        return fetch_recent_gmail_emails(account_id, max_results)
        
    # Check if it's a known Yahoo account
    yahoo_path = os.path.join(YAHOO_TOKEN_DIR, f"{account_id}.json")
    if os.path.exists(yahoo_path):
        return fetch_recent_yahoo_emails(account_id, max_results)
        
    return []

def fetch_all_recent_emails(max_results_per_account=5):
    """Iterates over ALL linked accounts and returns a combined list of emails."""
    all_emails = []
    accounts = list_all_accounts()
    for acc in accounts:
        print(f"Fetching from {acc['type']}:{acc['id']}...")
        emails = fetch_recent_emails(acc['id'], max_results=max_results_per_account)
        all_emails.extend(emails)
    return all_emails

# --- OTHER GOOGLE SERVICES ---

def delete_email(account_id, message_id):
    """Moves a specific email to trash (Gmail only currently)."""
    service = get_google_service('gmail', 'v1', account_id)
    if not service:
        # If it starts with yahoo_, we don't support delete yet
        if message_id.startswith("yahoo_"):
            print("Delete not supported for Yahoo yet.")
            return False
        return False
    try:
        service.users().messages().trash(userId='me', id=message_id).execute()
        return True
    except HttpError as error:
        print(f'An error occurred: {error}')
        return False

def fetch_upcoming_events(account_id='primary', max_results=10):
    """Lists the next N events on the user's primary calendar (Gmail accounts only)."""
    service = get_google_service('calendar', 'v3', account_id)
    if not service:
        return []

    try:
        now = datetime.datetime.now(datetime.UTC).isoformat().replace('+00:00', 'Z')
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=max_results, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        event_list = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            event_list.append({
                'account': account_id,
                'start': start,
                'summary': event.get('summary', 'No Title')
            })
        return event_list

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def upload_to_drive(file_path: str, folder_name: str = 'Morpheus-Backups', account_id: str = 'primary') -> bool:
    """Upload a file to a Google Drive folder."""
    from googleapiclient.http import MediaFileUpload
    service = get_google_service('drive', 'v3', account_id)
    if not service:
        return False

    try:
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])

        if folders:
            folder_id = folders[0]['id']
        else:
            folder_meta = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=folder_meta, fields='id').execute()
            folder_id = folder['id']

        file_name = os.path.basename(file_path)
        file_meta = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        service.files().create(body=file_meta, media_body=media, fields='id, name').execute()
        return True
    except Exception as e:
        print(f'Drive error: {e}')
        return False

if __name__ == '__main__':
    # Test all accounts
    all_mail = fetch_all_recent_emails(3)
    print(f"\nTotal emails found across all accounts: {len(all_mail)}")
    for i, e in enumerate(all_mail):
        print(f"{i+1}. [{e['type']}:{e['account']}] {e['subject']} (From: {e['from']})")
