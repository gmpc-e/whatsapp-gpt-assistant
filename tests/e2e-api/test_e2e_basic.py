import re
import pytest
from fastapi.testclient import TestClient

from app.main import app, pending
from app.models import IntentResult, EventCreate

client = TestClient(app)

class DummyIntent:
    def __init__(self, intent="EVENT_TASK"):
        self.intent = intent
        self.called_with = None

    def parse(self, text):
        self.called_with = text
        if self.intent == "EVENT_TASK":
            return IntentResult(
                intent="EVENT_TASK",
                event=EventCreate(
                    title="Dentist with Mom",
                    start_date="next tuesday",
                    start_time="10:00",
                    duration_minutes=30,
                    location="Tel Aviv",
                    notes="bring insurance"
                ),
                confidence=0.95,
            )
        return IntentResult(intent="QUESTION", answer="Some answer")

    def generate_answer(self, user_text, domain=None, recency_required=None):
        return "Here are three sci-fi movies: Interstellar, The Martian, Ender’s Game."

class DummyCalendar:
    def __init__(self):
        self.created = []
    def create_event(self, ev: EventCreate):
        self.created.append(ev)
        return "https://calendar.google.com/event?fake=1"

@pytest.fixture(autouse=True)
def patch_connectors(monkeypatch):
    # patch the intent connector instance used by the app
    from app import main as m
    dummy_intent = DummyIntent()
    dummy_calendar = DummyCalendar()
    monkeypatch.setattr(m, "intent", dummy_intent)
    monkeypatch.setattr(m, "calendar", dummy_calendar)
    yield

def test_create_event_preview_and_confirm():
    from_num = "whatsapp:+972500000000"

    # Step 1: initial message -> expect preview
    r1 = client.post("/whatsapp", data={
        "From": from_num,
        "Body": "please schedule dentist next tuesday 10:00 in tel aviv",
        "NumMedia": "0"
    })
    assert r1.status_code == 200
    xml = r1.text
    assert "Please confirm this event" in xml
    assert "Dentist with Mom" in xml
    # Pending confirmation stored:
    assert pending.has(from_num)

    # Step 2: confirm -> expect created
    r2 = client.post("/whatsapp", data={
        "From": from_num,
        "Body": "1",
        "NumMedia": "0"
    })
    assert r2.status_code == 200
    xml2 = r2.text
    assert "✅ Event added" in xml2
    # Store cleared
    assert not pending.has(from_num)

def test_general_question_path():
    from_num = "whatsapp:+972500000000"
    # Make the dummy intent answer as QUESTION
    from app import main as m
    m.intent.intent = "QUESTION"

    r = client.post("/whatsapp", data={
        "From": from_num,
        "Body": "What are three sci-fi movies for teens?",
        "NumMedia": "0"
    })
    assert r.status_code == 200
    assert "Echo:" not in r.text  # should not fall back to echo if we return an answer
