# app/deps.py
from pathlib import Path
from googleapiclient.discovery import build

from app.connectors.google_auth import get_credentials
from app.connectors.google_calendar import GoogleCalendarConnector
from app.connectors.google_tasks import GoogleTasksConnector

# Replace these imports with your actual implementations
from app.connectors.intent_router import IntentRouter
from app.connectors.whisper_stub import WhisperConnector
from app.connectors.media import MediaConnector
from app.connectors.messenger import MessengerConnector
from app.services.logger import get_logger

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _resolve_path(p: str) -> Path:
    # Useful for /debug
    return (PROJECT_ROOT / p).resolve()

def build_connectors():
    # One OAuth token for both Google Calendar + Tasks
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
    ]
    creds = get_credentials(scopes=SCOPES)

    # Google services
    calendar_service = build("calendar", "v3", credentials=creds)
    tasks_service = build("tasks", "v1", credentials=creds)

    logger = get_logger("assistant")

    # Domain connectors
    calendar = GoogleCalendarConnector(service=calendar_service, logger=logger)
    tasks = GoogleTasksConnector(service=tasks_service, logger=logger)

    # Other connectors (rename to your actual classes/modules)
    intent = IntentRouter(logger=logger)
    whisper = WhisperConnector(logger=logger)
    media = MediaConnector(logger=logger)
    messenger = MessengerConnector(logger=logger)

    # Keep this order; main.py unpacks it
    return intent, whisper, media, calendar, tasks, messenger, logger
