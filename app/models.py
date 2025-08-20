from typing import Optional, List, Literal, Dict, Any
from pydantic import BaseModel

# ---- Events ----

class EventCreate(BaseModel):
    title: str
    start_date: str
    start_time: str
    duration_minutes: int = 60
    location: Optional[str] = ""
    notes: Optional[str] = ""

class EventUpdateCriteria(BaseModel):
    who: Optional[str] = None
    date_hint: Optional[str] = None
    time_hint: Optional[str] = None
    title_hint: Optional[str] = None

class EventUpdateChanges(BaseModel):
    new_title: Optional[str] = None
    new_date: Optional[str] = None    # YYYY-MM-DD
    new_time: Optional[str] = None    # HH:MM
    new_duration_minutes: Optional[int] = None
    new_location: Optional[str] = None
    new_notes: Optional[str] = None

class EventUpdate(BaseModel):
    criteria: EventUpdateCriteria
    changes: EventUpdateChanges

# ---- Tasks ----

class TaskItem(BaseModel):
    title: str
    when: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None
    list_name: Optional[str] = None
    tags: Optional[List[str]] = None

class TaskOp(BaseModel):
    op: Literal["create","update","list","complete","delete"]
    criteria: Optional[Dict[str, Any]] = None
    tasks: Optional[List[TaskItem]] = None

# ---- Intent Result ----

class IntentResult(BaseModel):
    intent: Literal["QUESTION","EVENT_TASK","EVENT_UPDATE","TASK_OP","CHITCHAT"]
    answer: str
    event: Optional[EventCreate] = None
    events: Optional[List[EventCreate]] = None
    update: Optional[EventUpdate] = None
    task_op: Optional[TaskOp] = None
    confidence: Optional[float] = None
    recency_required: Optional[bool] = None
    domain: Optional[str] = None
