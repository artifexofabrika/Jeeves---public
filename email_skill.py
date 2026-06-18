import os, pickle, base64, re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = os.path.expanduser('~/credentials.json')
TOKEN_FILE = os.path.expanduser('~/token.pickle')

def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            auth_url, _ = flow.authorization_url(prompt='consent')
            print('Please go to this URL and authorize access:')
            print(auth_url)
            code = input('Enter the authorization code: ').strip()
            flow.fetch_token(code=code)
            creds = flow.credentials
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def check_email():
    try:
        service = get_gmail_service()
        results = service.users().messages().list(
            userId='me', labelIds=['INBOX'], q='is:unread', maxResults=5).execute()
        messages = results.get('messages', [])
        if not messages:
            return "You have no unread emails, sir."
        summary = "📬 Latest unread emails:\n"
        for msg in messages:
            txt = service.users().messages().get(
                userId='me', id=msg['id'], format='metadata',
                metadataHeaders=['From','Subject','Date']).execute()
            headers = txt['payload']['headers']
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            date = next(h['value'] for h in headers if h['name'] == 'Date')
            summary += f"• {sender} | {subject} | {date}\n"
        return summary
    except Exception as e:
        return f"I am unable to access the inbox at the moment, sir. Error: {e}"

def send_email(to, subject, body):
    try:
        service = get_gmail_service()
        message = f"From: me\r\nTo: {to}\r\nSubject: {subject}\r\n\r\n{body}"
        raw = base64.urlsafe_b64encode(message.encode('utf-8')).decode('utf-8')
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Email sent to {to}, sir."
    except Exception as e:
        return f"Failed to send email. Error: {e}"
