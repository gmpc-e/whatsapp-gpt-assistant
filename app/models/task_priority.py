"""Enhanced task models with priority support."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class TaskPriority(str, Enum):
    """Task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskCategory(str, Enum):
    """Task categories."""
    WORK = "work"
    PERSONAL = "personal"
    SHOPPING = "shopping"
    HEALTH = "health"
    FINANCE = "finance"
    OTHER = "other"


class EnhancedTaskItem(BaseModel):
    """Enhanced task item with priority and category."""
    title: str
    date: Optional[str] = None
    time: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    category: Optional[TaskCategory] = TaskCategory.OTHER
    
    def to_google_tasks_format(self) -> dict:
        """Convert to Google Tasks API format."""
        notes_parts = []
        if self.notes:
            notes_parts.append(self.notes)
        if self.priority and self.priority != TaskPriority.MEDIUM:
            notes_parts.append(f"Priority: {self.priority.value.title()}")
        if self.category and self.category != TaskCategory.OTHER:
            notes_parts.append(f"Category: {self.category.value.title()}")
        if self.location:
            notes_parts.append(f"Location: {self.location}")
        
        return {
            "title": self.title,
            "notes": "\n".join(notes_parts) if notes_parts else None,
            "date": self.date,
            "time": self.time,
        }
