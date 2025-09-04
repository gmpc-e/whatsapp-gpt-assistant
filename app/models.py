from __future__ import annotations

from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, model_validator


# -----------------------------
# Event creation (existing)
# -----------------------------
class EventCreate(BaseModel):
    """
    Canonical fields the app expects:
      - title: required
      - start_date: 'YYYY-MM-DD'
      - start_time: 'HH:MM' (optional)
      - duration_minutes: int (optional)
      - location: str (optional)
      - notes: str (optional)

    Backward-compat aliases accepted on input:
      - date -> start_date
      - time -> start_time
      - description -> notes
    """
    title: str
    start_date: str
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    location: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, v):
        if isinstance(v, dict):
            if "date" in v and "start_date" not in v:
                v["start_date"] = v.pop("date")
            if "time" in v and "start_time" not in v:
                v["start_time"] = v.pop("time")
            if "description" in v and "notes" not in v:
                v["notes"] = v.pop("description")
        return v
# -----------------------------
# Event update (existing)
# -----------------------------
class EventUpdateCriteria(BaseModel):
    who: Optional[str] = None
    date_hint: Optional[str] = None
    time_hint: Optional[str] = None
    title_hint: Optional[str] = None


class EventUpdateChanges(BaseModel):
    new_title: Optional[str] = None
    new_date: Optional[str] = None        # "YYYY-MM-DD"
    new_time: Optional[str] = None        # "HH:MM"
    new_duration_minutes: Optional[int] = None
    new_location: Optional[str] = None
    new_notes: Optional[str] = None


class EventUpdate(BaseModel):
    criteria: EventUpdateCriteria
    changes: EventUpdateChanges


# -----------------------------
# Listing (NEW)
# -----------------------------
class EventListQuery(BaseModel):
    scope: Literal["day", "week"]
    # optional anchor date (prefer ISO "YYYY-MM-DD"; router may also pass natural text)
    date_hint: Optional[str] = None


# -----------------------------
# Tasks (NEW – Google Tasks API)
# -----------------------------
class TaskItem(BaseModel):
    title: str
    date: Optional[str] = None            # "YYYY-MM-DD" (for due)
    time: Optional[str] = None            # "HH:MM" (optional)
    notes: Optional[str] = None
    location: Optional[str] = None        # stored inside notes (Tasks has no location field)
    list_hint: Optional[str] = None       # hint for which task list to use


class TaskUpdate(BaseModel):
    criteria: Dict[str, Any]              # e.g. {"title_hint": "Call Sarah", "date_hint": "tomorrow"}
    changes: Dict[str, Any]               # e.g. {"new_title":"..", "new_date":"..", "new_time":"..", "new_notes":".."}


class TaskOp(BaseModel):
    op: Literal["create", "update", "list", "complete", "delete"]
    # free-form for search/list/update – keep flexible
    criteria: Optional[Dict[str, Any]] = None


# -----------------------------
# Router result envelope
# -----------------------------
class IntentResult(BaseModel):
    # high-level routing
    intent: Optional[str] = None
    answer: str = ""  # <- was Optional[str] = None
    confidence: Optional[float] = None
    recency_required: Optional[bool] = None
    domain: Optional[str] = None

    # event create/update (existing)
    event: Optional[EventCreate] = None
    update: Optional[EventUpdate] = None

    # tasks (NEW)
    task_op: Optional[TaskOp] = None
    task: Optional[TaskItem] = None
    task_update: Optional[TaskUpdate] = None

    # listing (NEW)
    list_query: Optional[EventListQuery] = None
