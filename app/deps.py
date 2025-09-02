# app/deps.py
from pathlib import Path
from googleapiclient.discovery import build

from app.connectors.google_auth import get_credentials
from app.connectors.google_calendar import GoogleCalendarConnector
from app.connectors.google_tasks import GoogleTasksConnector

# --- Robust imports for intent/whisper/media/messenger/logger ---
def _try_import():
    connector_candidates = [
        ("app.connectors.intent_router", "IntentRouter"),
        ("app.intent_router", "IntentRouter"),
        ("app.connectors.intent", "IntentRouter"),
        ("app.intent", "IntentRouter"),
    ]
    whisper_candidates = [
        ("app.connectors.whisper_stub", "WhisperConnector"),
        ("app.whisper_stub", "WhisperConnector"),
        ("app.connectors.whisper", "WhisperConnector"),
        ("app.whisper", "WhisperConnector"),
    ]
    media_candidates = [
        ("app.connectors.media", "MediaConnector"),
        ("app.media", "MediaConnector"),
    ]
    messenger_candidates = [
        ("app.connectors.messenger", "MessengerConnector"),
        ("app.messenger", "MessengerConnector"),
    ]
    logger_candidates = [
        ("app.services.logger", "get_logger"),
        ("app.logger", "get_logger"),
    ]

    def _import(cands, fallback):
        for mod, name in cands:
            try:
                module = __import__(mod, fromlist=[name])
                return getattr(module, name)
            except Exception:
                continue
        return fallback

    # Fallback stubs (only if real modules aren’t found)
    import logging
    class _FallbackIntent:
        def __init__(self, logger=None): self.logger = logger
        def parse(self, text):
            from app.models import IntentResult
            return IntentResult(intent="GENERAL_QA", confidence=0.5)
        def generate_answer(self, q, **kwargs): return None

    class _FallbackWhisper:
        def __init__(self, logger=None): self.logger = logger
        def transcribe(self, b, filename=None): return ""

    class _FallbackMedia:
        class Payload:
            def __init__(self): self.bytes = b""; self.filename = "audio.ogg"
        def __init__(self, logger=None): self.logger = logger
        def fetch(self, form): return self.Payload()

    class _FallbackMessenger:
        def __init__(self, logger=None): self.logger = logger
        def send(self, text):
            logging.getLogger("assistant").info("Messenger(send): %s", text)

    def _fallback_get_logger(name):
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(name)

    Intent = _import(connector_candidates, _FallbackIntent)
    Whisper = _import(whisper_candidates, _FallbackWhisper)
    Media = _import(media_candidates, _FallbackMedia)
    Messenger = _import(messenger_candidates, _FallbackMessenger)
    get_logger_fn = _import(logger_candidates, _fallback_get_logger)
    return Intent, Whisper, Media, Messenger, get_logger_fn

IntentRouter, WhisperConnector, MediaConnector, MessengerConnector, get_logger = _try_import()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def _resolve_path(p: str) -> Path:
    return (PROJECT_ROOT / p).resolve()

def build_connectors():
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/tasks",
    ]
    creds = get_credentials(scopes=SCOPES)

    # ✅ Build the Calendar service here and pass it into the connector
    calendar_service = build("calendar", "v3", credentials=creds)

    logger = get_logger("assistant")

    calendar = GoogleCalendarConnector(calendar_service, logger=logger)  # <-- positional
    tasks = GoogleTasksConnector(logger=logger)  # your Tasks connector builds its own service

    intent = IntentRouter(logger=logger)
    whisper = WhisperConnector(logger=logger)
    media = MediaConnector(logger=logger)
    messenger = MessengerConnector(logger=logger)

    return intent, whisper, media, calendar, tasks, messenger, logger
