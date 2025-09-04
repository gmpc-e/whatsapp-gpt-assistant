"""Models package for the WhatsApp GPT Assistant."""

from __future__ import annotations

from typing import Optional, Literal, List, Dict, Any
from pydantic import BaseModel, Field, model_validator

from .task_priority import TaskPriority, TaskCategory, EnhancedTaskItem

class EventCreate(BaseModel):
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

class EventUpdateCriteria(BaseModel):
    who: Optional[str] = None
    date_hint: Optional[str] = None
    time_hint: Optional[str] = None
    title_hint: Optional[str] = None

class EventUpdateChanges(BaseModel):
    new_title: Optional[str] = None
    new_date: Optional[str] = None
    new_time: Optional[str] = None
    new_duration_minutes: Optional[int] = None
    new_location: Optional[str] = None
    new_notes: Optional[str] = None

class EventUpdate(BaseModel):
    criteria: EventUpdateCriteria
    changes: EventUpdateChanges

class EventListQuery(BaseModel):
    scope: Literal["day", "week"]
    date_hint: Optional[str] = None

class TaskItem(BaseModel):
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None

class TaskUpdate(BaseModel):
    criteria: Dict[str, Any]
    changes: Dict[str, Any]

class TaskOp(BaseModel):
    op: Literal["create", "update", "list", "complete", "delete"]
    criteria: Optional[Dict[str, Any]] = None

class IntentResult(BaseModel):
    intent: Optional[str] = None
    answer: str = ""
    confidence: Optional[float] = None
    recency_required: Optional[bool] = None
    domain: Optional[str] = None
    event: Optional[EventCreate] = None
    update: Optional[EventUpdate] = None
    task_op: Optional[TaskOp] = None
    task: Optional[TaskItem] = None
    task_update: Optional[TaskUpdate] = None
    list_query: Optional[EventListQuery] = None

__all__ = [
    "TaskPriority", 
    "TaskCategory", 
    "EnhancedTaskItem",
    "EventCreate",
    "EventUpdate",
    "EventUpdateChanges",
    "EventUpdateCriteria",
    "EventListQuery",
    "TaskItem",
    "TaskUpdate",
    "TaskOp",
    "IntentResult"
]
