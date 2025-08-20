import json
import datetime as dt
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

from app.models import EventCreate, EventUpdate, EventUpdateChanges
from app.utils.time_utils import normalize_event_datetimes, normalize_free_datetime
from app.config import settings

class GoogleCalendarConnector:
    def __init__(self, gcal_service, logger):
        self.svc = gcal_service
        self.logger = logger

    # ---- Create ----
    def create_event(self, event: EventCreate) -> Optional[str]:
        start_dt, end_dt = normalize_event_datetimes(event, settings.TIMEZONE)
        body = {
            "summary": event.title or "Untitled",
            "location": event.location or "",
            "description": event.notes or "",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": settings.TIMEZONE},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": settings.TIMEZONE},
            "reminders": {"useDefault": True},
        }
        if settings.DEBUG_LOG_PROMPTS:
            self.logger.info("[GCAL] Creating: %s", json.dumps(body, ensure_ascii=False))
        created = self.svc.events().insert(calendarId="primary", body=body).execute()
        link = created.get("htmlLink")
        if settings.DEBUG_LOG_PROMPTS:
            self.logger.info("[GCAL] Created -> %s", json.dumps(created, ensure_ascii=False))
        return link

    # ---- Search for update candidates ----
    def search_events_window(self, start: dt.datetime, end: dt.datetime) -> List[Dict[str, Any]]:
        timeMin = start.isoformat()
        timeMax = end.isoformat()
        res = self.svc.events().list(
            calendarId="primary",
            timeMin=timeMin,
            timeMax=timeMax,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        return res.get("items", [])

    def find_candidates(self, criteria, window_days: int = 7) -> List[Dict[str, Any]]:
        tz = ZoneInfo(settings.TIMEZONE)
        # Build a date window around date_hint if present, else next 7 days
        base = normalize_free_datetime(criteria.date_hint, settings.TIMEZONE) if criteria and criteria.date_hint else None
        if not base:
            base = dt.datetime.now(tz)
        start = base.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + dt.timedelta(days=window_days)
        items = self.search_events_window(start, end)

        filtered = []
        who = (criteria.who or "").lower() if criteria and criteria.who else ""
        title_hint = (criteria.title_hint or "").lower() if criteria and criteria.title_hint else ""
        time_hint = (criteria.time_hint or "").lower() if criteria and criteria.time_hint else ""

        for ev in items:
            summary = (ev.get("summary") or "").lower()
            if who and who not in summary:
                continue
            if title_hint and title_hint not in summary:
                continue
            # time hint heuristic
            if time_hint and time_hint in {"morning","afternoon","evening"}:
                try:
                    start_iso = ev["start"].get("dateTime") or ev["start"].get("date")
                    if start_iso:
                        t = dt.datetime.fromisoformat(start_iso.replace("Z","+00:00")).astimezone(tz)
                        hour = t.hour
                        if time_hint == "morning" and not (6 <= hour <= 11): continue
                        if time_hint == "afternoon" and not (12 <= hour <= 17): continue
                        if time_hint == "evening" and not (18 <= hour <= 22): continue
                except Exception:
                    pass
            filtered.append(ev)

        return filtered

    # ---- Update ----
    def apply_update(self, event_obj: Dict[str, Any], changes: EventUpdateChanges) -> Dict[str, Any]:
        tz = settings.TIMEZONE
        patched = {}

        # title
        if changes.new_title:
            patched["summary"] = changes.new_title

        # description/notes
        if changes.new_notes is not None:
            patched["description"] = changes.new_notes

        # location
        if changes.new_location is not None:
            patched["location"] = changes.new_location

        # time/date/duration
        # Start from existing start
        start_iso = event_obj["start"].get("dateTime") or event_obj["start"].get("date")
        if start_iso and "T" in start_iso:
            start_dt = dt.datetime.fromisoformat(start_iso.replace("Z","+00:00"))
        else:
            # all-day -> set a default time 09:00
            hint_date = changes.new_date or start_iso or ""
            nd = normalize_free_datetime(hint_date, tz) if hint_date else None
            start_dt = nd or dt.datetime.now()

        # apply date/time overrides
        date_phrase = changes.new_date or start_dt.date().isoformat()
        time_phrase = changes.new_time or start_dt.strftime("%H:%M")
        from app.models import EventCreate as EC
        sdt, edt = normalize_event_datetimes(EC(
            title=patched.get("summary") or event_obj.get("summary") or "Untitled",
            start_date=date_phrase,
            start_time=time_phrase,
            duration_minutes=changes.new_duration_minutes or 60,
            location=patched.get("location") or event_obj.get("location") or "",
            notes=patched.get("description") or event_obj.get("description") or "",
        ), tz)

        patched["start"] = {"dateTime": sdt.isoformat(), "timeZone": tz}
        patched["end"] = {"dateTime": edt.isoformat(), "timeZone": tz}

        # Patch via API
        ev_id = event_obj["id"]
        updated = self.svc.events().patch(calendarId="primary", eventId=ev_id, body=patched).execute()
        return updated
