import datetime as dt
from zoneinfo import ZoneInfo
import dateparser

from app.models import EventCreate
from app.config import settings

def normalize_event_datetimes(event: EventCreate, timezone: str):
    tz = ZoneInfo(timezone)
    now = dt.datetime.now(tz)
    phrase = f"{event.start_date} {event.start_time}".strip() or "in 1 hour"
    settings_dp = {
        "TIMEZONE": timezone,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now,
    }
    start_dt = dateparser.parse(phrase, settings=settings_dp) or (now + dt.timedelta(hours=1))
    while start_dt <= now:
        try:
            start_dt = start_dt.replace(year=start_dt.year + 1)
        except ValueError:
            start_dt += dt.timedelta(days=365)
    end_dt = start_dt + dt.timedelta(minutes=event.duration_minutes or 60)
    return start_dt, end_dt

def normalize_free_datetime(phrase: str, timezone: str):
    tz = ZoneInfo(timezone)
    now = dt.datetime.now(tz)
    settings_dp = {
        "TIMEZONE": timezone,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "PREFER_DATES_FROM": "future",
        "RELATIVE_BASE": now,
    }
    dt_parsed = dateparser.parse(phrase or "", settings=settings_dp)
    return dt_parsed
