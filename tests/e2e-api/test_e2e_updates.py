# tests/e2e-api/test_e2e_updates.py
import pytest
from fastapi.testclient import TestClient

from app.main import app, pending
from app.models import IntentResult, EventUpdate, EventUpdateChanges, EventUpdateCriteria

client = TestClient(app)

# ------------------ Test Doubles ------------------

class DummyIntentUpdate:
    """
    Always returns EVENT_UPDATE with provided criteria+changes.
    Adjust per test to simulate time/date/location/title/notes changes.
    """
    def __init__(self, who=None, date_hint=None, time_hint=None, title_hint=None, changes=None):
        self.criteria = EventUpdateCriteria(
            who=who, date_hint=date_hint, time_hint=time_hint, title_hint=title_hint
        )
        self.changes = changes or EventUpdateChanges(new_time="18:00")
        self.called_with = None

    def parse(self, text: str):
        self.called_with = text
        return IntentResult(
            intent="EVENT_UPDATE",
            update=EventUpdate(criteria=self.criteria, changes=self.changes),
            confidence=0.95,
        )

def _gcal_event(event_id: str, title: str, dt_iso: str):
    """Minimal Google-like event dict."""
    return {
        "id": event_id,
        "summary": title,
        "start": {"dateTime": dt_iso},
        "end": {"dateTime": dt_iso},
        "location": "",
        "description": "",
        "htmlLink": f"https://calendar.google.com/event?eid={event_id}",
    }

class DummyCalendar:
    """Calendar stub with injectable candidates and a simple apply_update."""
    def __init__(self, candidates):
        self._candidates = candidates
        self.apply_calls = []

    def find_candidates(self, criteria, window_days=7):
        return list(self._candidates)

    def apply_update(self, ev_obj, changes: EventUpdateChanges):
        self.apply_calls.append((ev_obj, changes))
        updated = dict(ev_obj)
        title = updated.get("summary", "(no title)")
        if changes.new_title:
            title = changes.new_title
        start_iso = updated["start"].get("dateTime") or updated["start"].get("date") or ""
        updated["summary"] = title
        updated["start"] = {"dateTime": start_iso}
        return updated

# ------------------ Fixtures / Helpers ------------------

@pytest.fixture(autouse=True)
def isolate_pending_store():
    """Clear PendingStore before/after each test."""
    pending._store.clear()
    yield
    pending._store.clear()

def post_whatsapp(from_num: str, body: str, num_media: int = 0):
    return client.post("/whatsapp", data={"From": from_num, "Body": body, "NumMedia": str(num_media)})

# ------------------ Tests ------------------

def test_update_time_single_candidate(monkeypatch):
    """Single match → go straight to confirm, then apply update."""
    from app import main as m
    intent_stub = DummyIntentUpdate(who="David", date_hint="Thursday", changes=EventUpdateChanges(new_time="18:00"))
    cal_stub = DummyCalendar([_gcal_event("ev1", "Meeting with David", "2025-09-04T15:00:00+03:00")])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move the meeting with David on Thursday to 18:00")
    assert "Found one match" in r1.text
    r2 = post_whatsapp(from_num, "1")
    assert "✅ Updated:" in r2.text
    assert len(cal_stub.apply_calls) == 1
    assert not pending.has(from_num)

def test_update_date_single_candidate(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(who="Sarah", date_hint="Tuesday", changes=EventUpdateChanges(new_date="Friday"))
    cal_stub = DummyCalendar([_gcal_event("ev2", "1:1 with Sarah", "2025-09-02T09:00:00+03:00")])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move Sarah meeting from Tuesday to Friday")
    assert "Found one match" in r1.text
    r2 = post_whatsapp(from_num, "confirm")
    assert "✅ Updated:" in r2.text
    assert len(cal_stub.apply_calls) == 1
    assert not pending.has(from_num)

def test_update_location_single_candidate(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(who="Mom", date_hint="tomorrow", changes=EventUpdateChanges(new_location="Her house"))
    cal_stub = DummyCalendar([_gcal_event("ev3", "Meeting with Mom", "2025-09-02T18:00:00+03:00")])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Update tomorrow’s meeting with Mom to be at her house")
    assert "Found one match" in r1.text
    r2 = post_whatsapp(from_num, "1")
    assert "✅ Updated:" in r2.text
    assert len(cal_stub.apply_calls) == 1
    assert not pending.has(from_num)

def test_update_rename_and_notes_single_candidate(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(
        who="Dentist", date_hint="next Monday",
        changes=EventUpdateChanges(new_title="Dentist Dr. Cohen", new_notes="Bring insurance card"),
    )
    cal_stub = DummyCalendar([_gcal_event("ev4", "Dentist appointment", "2025-09-08T10:30:00+03:00")])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Rename dentist appointment next Monday to Dentist Dr. Cohen")
    assert "Found one match" in r1.text
    r2 = post_whatsapp(from_num, "confirm")
    assert "✅ Updated:" in r2.text
    assert len(cal_stub.apply_calls) == 1
    assert not pending.has(from_num)

def test_update_disambiguation_multiple_candidates(monkeypatch):
    """Multiple matches → disambiguate → select → confirm."""
    from app import main as m
    intent_stub = DummyIntentUpdate(who="Sarah", date_hint="next week", changes=EventUpdateChanges(new_time="10:00"))
    cal_stub = DummyCalendar([
        _gcal_event("ev5", "Weekly sync with Sarah", "2025-09-09T09:00:00+03:00"),
        _gcal_event("ev6", "Planning with Sarah", "2025-09-11T11:00:00+03:00"),
    ])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move next week’s Sarah meeting to 10:00")
    assert ("multiple" in r1.text.lower()) or ("choose" in r1.text.lower())
    assert pending.has(from_num)

    # choose option 2
    r2 = post_whatsapp(from_num, "2")
    assert "Confirm update?" in r2.text
    # confirm
    r3 = post_whatsapp(from_num, "1")
    assert "✅ Updated:" in r3.text
    assert not pending.has(from_num)
    assert len(cal_stub.apply_calls) == 1
    ev_obj, _ = cal_stub.apply_calls[0]
    assert ev_obj["id"] == "ev6"

def test_update_no_candidates(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(who="Tom", date_hint="Thursday", changes=EventUpdateChanges(new_time="16:00"))
    cal_stub = DummyCalendar([])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move Tom meeting on Thursday to 16:00")
    assert "couldn't find a matching event" in r1.text.lower()
    assert not pending.has(from_num)

def test_update_cancel_in_select(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(who="Sarah", date_hint="tomorrow", changes=EventUpdateChanges(new_time="17:00"))
    cal_stub = DummyCalendar([
        _gcal_event("ev7", "Catch-up with Sarah", "2025-09-02T16:00:00+03:00"),
        _gcal_event("ev8", "Review with Sarah", "2025-09-02T18:00:00+03:00"),
    ])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move Sarah meeting tomorrow to 17:00")
    assert ("multiple" in r1.text.lower()) or ("choose" in r1.text.lower())
    r2 = post_whatsapp(from_num, "0")  # cancel
    assert "cancelled" in r2.text.lower()
    assert not pending.has(from_num)

def test_update_cancel_in_confirm(monkeypatch):
    from app import main as m
    intent_stub = DummyIntentUpdate(who="David", date_hint="Friday", changes=EventUpdateChanges(new_time="18:00"))
    cal_stub = DummyCalendar([_gcal_event("ev9", "Meeting with David", "2025-09-05T12:00:00+03:00")])
    monkeypatch.setattr(m, "intent", intent_stub)
    monkeypatch.setattr(m, "calendar", cal_stub)

    from_num = "whatsapp:+972500000000"
    r1 = post_whatsapp(from_num, "Move Friday meeting with David to 18:00")
    assert "Found one match" in r1.text
    r2 = post_whatsapp(from_num, "cancel")
    assert "cancelled" in r2.text.lower()
    assert not pending.has(from_num)
