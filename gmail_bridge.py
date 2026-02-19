import datetime
import os.path
import base64
import glob
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the token files.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/drive.file'   # upload files the app creates
]

# Handle absolute paths for Docker/Cron execution
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_DIR = os.path.join(ROOT_DIR, 'tokens', 'gmail')
CREDENTIALS_FILE = os.path.join(ROOT_DIR, 'credentials.json')

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
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build(service_name, version, credentials=creds)
        return service
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def list_accounts():
    """Lists all Gmail account IDs that have a stored token."""
    if not os.path.exists(TOKEN_DIR):
        return []
    files = glob.glob(os.path.join(TOKEN_DIR, "*.json"))
    return [os.path.basename(f).replace(".json", "") for f in files]

def fetch_recent_emails(account_id='primary', max_results=5):
    """Fetches the last N emails from the inbox for a specific account."""
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
                'snippet': snippet
            })
            
        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def delete_email(account_id, message_id):
    """Moves a specific email to trash."""
    service = get_google_service('gmail', 'v1', account_id)
    if not service:
        return False
    try:
        service.users().messages().trash(userId='me', id=message_id).execute()
        return True
    except HttpError as error:
        print(f'An error occurred: {error}')
        return False

def fetch_upcoming_events(account_id='primary', max_results=10):
    """Lists the next N events on the user's primary calendar for a specific account."""
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

def fetch_recent_files(account_id='primary', max_results=5):
    """Lists the last N modified files from Google Drive for a specific account."""
    service = get_google_service('drive', 'v3', account_id)
    if not service:
        return []

    try:
        results = service.files().list(
            pageSize=max_results, 
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()
        files = results.get('files', [])

        file_list = []
        for file in files:
            file_list.append({
                'account': account_id,
                'name': file['name'],
                'type': file['mimeType'],
                'modified': file['modifiedTime']
            })
        return file_list

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def upload_to_drive(file_path: str, folder_name: str = 'Morpheus-Backups', account_id: str = 'primary') -> bool:
    """Upload a file to a Google Drive folder. Creates the folder if it doesn't exist."""
    from googleapiclient.http import MediaFileUpload
    import os

    service = get_google_service('drive', 'v3', account_id)
    if not service:
        return False

    try:
        # Find or create the target folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields='files(id, name)').execute()
        folders = results.get('files', [])

        if folders:
            folder_id = folders[0]['id']
        else:
            # Create the folder
            folder_meta = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_meta, fields='id').execute()
            folder_id = folder['id']
            print(f'  [drive] Created folder: {folder_name}')

        # Upload the file
        file_name = os.path.basename(file_path)
        file_meta = {'name': file_name, 'parents': [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        uploaded = service.files().create(body=file_meta, media_body=media, fields='id, name').execute()
        print(f'  [drive] Uploaded: {uploaded["name"]} (id: {uploaded["id"]})')
        return True

    except HttpError as error:
        print(f'  [drive] Upload error: {error}')
        return False

if __name__ == '__main__':
    accounts = list_accounts()
    print(f"Found accounts: {accounts}")
    
    for acc in accounts:
        print(f"\n--- Account: {acc} ---")
        print("Testing Gmail...")
        emails = fetch_recent_emails(acc, 3)
        for i, e in enumerate(emails):
            print(f"{i+1}. {e['subject']} - From: {e['from']}")
            
        print("\nTesting Calendar...")
        events = fetch_upcoming_events(acc, 5)
        for event in events:
            print(f"{event['start']} - {event['summary']}")

        print("\nTesting Drive...")
        files = fetch_recent_files(acc, 5)
        for f in files:
            print(f"[{f['type']}] {f['name']} (Modified: {f['modified']})")
