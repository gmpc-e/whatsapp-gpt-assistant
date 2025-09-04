# app/connectors/google_tasks.py
"""
Google Tasks connector (real API).
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
import datetime as dt
import json

from zoneinfo import ZoneInfo
from app.config import settings
from app.connectors.google_auth import get_credentials

try:
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover
    build = None


def _to_rfc3339_due(date_str: Optional[str], time_str: Optional[str]) -> Optional[str]:
    if not date_str and not time_str:
        return None
    tz = ZoneInfo(settings.TIMEZONE)
    if date_str:
        y, m, d = map(int, date_str.split("-"))
    else:
        now = dt.datetime.now(tz)
        y, m, d = now.year, now.month, now.day
    if time_str:
        hh, mm = map(int, time_str.split(":"))
        local_dt = dt.datetime(y, m, d, hh, mm, tzinfo=tz)
    else:
        local_dt = dt.datetime(y, m, d, 23, 59, tzinfo=tz)
    return local_dt.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _notes_with_location(notes: Optional[str], location: Optional[str]) -> Optional[str]:
    if location and notes:
        return f"{notes}\nLocation: {location}"
    if location:
        return f"Location: {location}"
    return notes


def _matches_criteria(task: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
    title_hint = (criteria or {}).get("title_hint")
    date_hint = (criteria or {}).get("date_hint")
    include_completed = (criteria or {}).get("include_completed", False)

    status = (task.get("status") or "").lower()
    if status == "completed" and not include_completed:
        return False

    if title_hint and title_hint.lower() not in (task.get("title") or "").lower():
        return False

    if date_hint:
        due = task.get("due")
        if not due:
            return False
        try:
            if due.endswith("Z"):
                dt_utc = dt.datetime.fromisoformat(due.replace("Z", "+00:00"))
            else:
                dt_utc = dt.datetime.fromisoformat(due)
            local_date = dt_utc.astimezone(ZoneInfo(settings.TIMEZONE)).date().isoformat()
            if local_date != date_hint:
                return False
        except Exception:
            return False
    return True


class GoogleTasksConnector:
    """Minimal wrapper around Google Tasks API."""

    SCOPES = ["https://www.googleapis.com/auth/tasks"]

    def __init__(self, logger=None):
        self.logger = logger
        self._service = None
        self._tasklist_id_cache = None
        if build is None and self.logger:
            self.logger.warning("googleapiclient not installed; GoogleTasksConnector disabled.")

    def _get_service(self):
        if self._service is not None:
            return self._service
        if build is None:
            raise NotImplementedError("Google Tasks client not available (googleapiclient missing).")
        # Use the shared token.json with both scopes; this call refreshes if needed
        creds = get_credentials(scopes=self.SCOPES)
        self._service = build("tasks", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def _get_tasklist_id(self) -> str:
        if self._tasklist_id_cache:
            return self._tasklist_id_cache
        name = getattr(settings, "GTASKS_TASKLIST_NAME", "Tasks")
        svc = self._get_service()
        page_token = None
        while True:
            resp = svc.tasklists().list(maxResults=100, pageToken=page_token).execute()
            for item in resp.get("items", []):
                if item.get("title") == name:
                    self._tasklist_id_cache = item["id"]
                    return self._tasklist_id_cache
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        created = svc.tasklists().insert(body={"title": name}).execute()
        self._tasklist_id_cache = created["id"]
        return self._tasklist_id_cache

    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not item.get("title"):
            raise ValueError("Task title is required")
        
        try:
            svc = self._get_service()
            tasklist_id = self._get_tasklist_id()
            body = {
                "title": item["title"],
                "notes": _notes_with_location(item.get("notes"), item.get("location")),
                "status": "needsAction",
            }
            due = _to_rfc3339_due(item.get("date"), item.get("time"))
            if due:
                body["due"] = due
            return svc.tasks().insert(tasklist=tasklist_id, body=body).execute()
        except Exception as e:
            if self.logger:
                self.logger.error("Failed to create task: %s", e)
            raise

    def list(self, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        svc = self._get_service()
        tasklist_id = self._get_tasklist_id()
        show_completed = (criteria or {}).get("include_completed", False)

        items: List[Dict[str, Any]] = []
        page_token = None
        while True:
            resp = svc.tasks().list(
                tasklist=tasklist_id,
                showCompleted=show_completed,
                showHidden=False,
                maxResults=100,
                pageToken=page_token,
            ).execute()
            for t in resp.get("items", []):
                if _matches_criteria(t, criteria or {}):
                    items.append(t)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items

    def update(self, criteria: Dict[str, Any], changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        svc = self._get_service()
        tasklist_id = self._get_tasklist_id()
        matches = self.list(criteria)
        updated: List[Dict[str, Any]] = []
        for t in matches:
            body = {"title": t.get("title"), "notes": t.get("notes"), "status": t.get("status")}
            if changes.get("new_title"):
                body["title"] = changes["new_title"]
            if "new_notes" in changes:
                body["notes"] = changes["new_notes"]
            if changes.get("new_date") or changes.get("new_time"):
                body["due"] = _to_rfc3339_due(changes.get("new_date"), changes.get("new_time"))
            res = svc.tasks().patch(tasklist=tasklist_id, task=t["id"], body=body).execute()
            updated.append(res)
        return updated

    def complete(self, criteria: Dict[str, Any]) -> int:
        svc = self._get_service()
        tasklist_id = self._get_tasklist_id()
        matches = self.list(criteria)
        count = 0
        for t in matches:
            if (t.get("status") or "").lower() != "completed":
                body = {"status": "completed", "completed": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"}
                svc.tasks().patch(tasklist=tasklist_id, task=t["id"], body=body).execute()
                count += 1
        return count

    def delete(self, criteria: Dict[str, Any]) -> int:
        svc = self._get_service()
        tasklist_id = self._get_tasklist_id()
        matches = self.list(criteria)
        count = 0
        for t in matches:
            svc.tasks().delete(tasklist=tasklist_id, task=t["id"]).execute()
            count += 1
        return count
