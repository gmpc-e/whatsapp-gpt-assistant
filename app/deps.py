import os
from dotenv import load_dotenv
from openai import OpenAI
from twilio.rest import Client as TwilioClient
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings
from app.utils.logging import get_logger
from app.connectors.openai_intent import OpenAIIntentConnector
from app.connectors.openai_whisper import OpenAIWhisperConnector
from app.connectors.google_calendar import GoogleCalendarConnector
from app.connectors.twilio_messenger import TwilioMessenger
from app.connectors.media_fetch import TwilioMediaFetcher
from app.connectors.tasks_anydo import AnyDoConnector
from app.connectors.tasks_google import GoogleTasksConnector

SCOPES = ["https://www.googleapis.com/auth/calendar"]

load_dotenv()
logger = get_logger()

def get_openai_client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)

def get_twilio_client():
    return TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def get_google_calendar_service():
    creds = None
    if os.path.exists(settings.GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(settings.GOOGLE_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(settings.GOOGLE_CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(settings.GOOGLE_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def build_connectors():
    oa = get_openai_client()
    tw = get_twilio_client()
    gcal = get_google_calendar_service()

    intent = OpenAIIntentConnector(oa, logger, debug=settings.DEBUG_LOG_PROMPTS)
    whisper = OpenAIWhisperConnector(oa)
    media = TwilioMediaFetcher(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    calendar = GoogleCalendarConnector(gcal, logger)
    messenger = TwilioMessenger(tw, settings.TWILIO_WHATSAPP_NUMBER, settings.USER_WHATSAPP_NUMBER)

    # Tasks connectors: prefer Any.do if configured, else GoogleTasks fallback
    try:
        anydo = AnyDoConnector()
        # probe: this will raise if not configured
        _ = anydo.base and anydo.token
        tasks = anydo
    except Exception:
        tasks = GoogleTasksConnector()

    return intent, whisper, media, calendar, messenger, tasks, logger
