# app/deps.py
from __future__ import annotations
from pathlib import Path
import logging

from googleapiclient.discovery import build

from app.connectors.google_auth import get_credentials
from app.connectors.google_calendar import GoogleCalendarConnector
from app.connectors.google_tasks import GoogleTasksConnector
from app.models import IntentResult  # your Pydantic models (for the router stub)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _resolve_path(p: str) -> Path:
    return (PROJECT_ROOT / p).resolve()

# ----- Try to import your real connectors. If not found, provide stubs. -----
try:
    from app.connectors.intent_router import IntentRouter  # <- use your real router if available
except Exception:
    class IntentRouter:
        def __init__(self, logger=None): self.logger = logger
        def parse(self, text: str) -> IntentResult:
            # Minimal “always QA” fallback
            return IntentResult(intent="QUESTION", answer=None, confidence=0.7)
        def generate_answer(self, text: str, domain=None, recency_required=None) -> str | None:
            return None  # let main.py fall back to echo

try:
    from app.connectors.whisper_stub import WhisperConnector  # or your real Whisper connector
except Exception:
    class WhisperConnector:
        def __init__(self, logger=None): self.logger = logger
        def transcribe(self, audio_bytes: bytes, filename: str | None = None) -> str:
            return ""  # noop

try:
    from app.connectors.media import MediaConnector
except Exception:
    class _Payload:
        def __init__(self, bytes_: bytes = b"", filename: str | None = None):
            self.bytes = bytes_
            self.filename = filename or "voice.wav"
    class MediaConnector:
        def __init__(self, logger=None): self.logger = logger
        def fetch(self, form) -> _Payload:
            # Minimal Twilio form support
            url = form.get("MediaUrl0")
            if not url:
                return _Payload()
            # In a real impl: download the URL. For stub purposes return empty.
            return _Payload()

try:
    from app.connectors.messenger import MessengerConnector
except Exception:
    class MessengerConnector:
        def __init__(self, logger=None): self.logger = logger
        def send(self, text: str) -> None:
            (self.logger or logging.getLogger("messenger")).info("Messenger send: %s", text)

def get_logger(name: str = "assistant"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(h)
    return logger

def build_connectors():
    # One OAuth token for both Calendar + Tasks
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

    # Other connectors (real if available, otherwise stubs above)
    intent = IntentRouter(logger=logger)
    whisper = WhisperConnector(logger=logger)
    media = MediaConnector(logger=logger)
    messenger = MessengerConnector(logger=logger)

    # Keep this exact order; main.py unpacks it
    return intent, whisper, media, calendar, tasks, messenger, logger
