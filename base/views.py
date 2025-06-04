from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from django.conf import settings
import os
import pickle
import google.generativeai as genai
from datetime import datetime, timedelta
import calendar
import base64
import email

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyAIgQ-7qB4-o661he8cwRU61F2S9iOGkgs')  # Replace with your API key
genai.configure(api_key=GEMINI_API_KEY)

# Google Calendar and Gmail OAuth setup
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/gmail.readonly'  # Added for email fetching
]
CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'credentials.json')

@login_required
def email_summarizer(request):
    # Handle Google Calendar and Gmail authentication
    credentials = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if 'code' in request.GET:
            return google_callback(request)
        else:
            flow = Flow.from_client_secrets_file(
                CREDENTIALS_FILE,
                scopes=SCOPES,
                redirect_uri='http://localhost:8000/google/callback/'
            )
            auth_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            request.session['state'] = state
            return redirect(auth_url)

    # Fetch calendar events for April 2024
    service = build('calendar', 'v3', credentials=credentials)
    start_of_month = datetime(2024, 4, 1)
    end_of_month = start_of_month + timedelta(days=30)
    events_result = service.events().list(
        calendarId='primary',
        timeMin=start_of_month.isoformat() + 'Z',
        timeMax=end_of_month.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    # Highlight dates with events
    highlighted_dates = set()
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        event_date = datetime.strptime(start[:10], '%Y-%m-%d').day
        highlighted_dates.add(event_date)

    # Generate calendar for April 2024
    cal = calendar.monthcalendar(2024, 4)

    # Fetch emails using Gmail API
    gmail_service = build('gmail', 'v1', credentials=credentials)
    results = gmail_service.users().messages().list(userId='me', maxResults=2).execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        msg_data = gmail_service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        headers = msg_data['payload']['headers']
        subject = next(header['value'] for header in headers if header['name'] == 'Subject')
        
        # Extract email body
        parts = msg_data['payload'].get('parts', [])
        body = ''
        if parts:
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        else:
            body = base64.urlsafe_b64decode(msg_data['payload']['body']['data']).decode('utf-8')
        
        emails.append({'subject': subject, 'body': body[:500]})  # Limit body length for summarization

    # Summarize emails using Gemini API
    summaries = []
    model = genai.GenerativeModel('gemini-1.5-pro-latest')  # Update model name if needed
    for email in emails:
        prompt = f"Summarize this email and extract meeting details:\nSubject: {email['subject']}\nBody: {email['body']}"
        try:
            response = model.generate_content(prompt)
            summary = response.text
        except Exception as e:
            summary = f"Error summarizing email: {str(e)}"
        summaries.append({'subject': email['subject'], 'summary': summary})

    context = {
        'summaries': summaries,
        'calendar': cal,
        'month': 'April 2024',
        'highlighted_dates': highlighted_dates,
    }
    return render(request, 'email_summarizer.html', context)

def google_callback(request):
    state = request.session.get('state')
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri='http://localhost:8000/google/callback/'
    )
    flow.fetch_token(code=request.GET.get('code'))
    credentials = flow.credentials
    with open('token.pickle', 'wb') as token:
        pickle.dump(credentials, token)
    return redirect('base:email_summarizer')

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome!')
            return redirect('base:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def home(request):
    return render(request, 'home.html', {'user': request.user})