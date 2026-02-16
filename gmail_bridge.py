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
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
]

TOKEN_DIR = os.path.join('tokens', 'gmail')

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
                'credentials.json', SCOPES)
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
