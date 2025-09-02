"""
Google Tasks connector (real API).

Provides:
- create(item)
- list(criteria)
- update(criteria, changes)
- complete(criteria)
- delete(criteria)

Notes:
- Google Tasks does not have a native 'location' field. We store location inside notes (if given).
- 'due' must be RFC3339; we convert local date/time (settings.TIMEZONE) into UTC.
- Matching by criteria is done locally (title substring, optional date).
"""

from __future__ import annotations

import datetime as dt
from typing import Dict, Any, List, Optional

from zoneinfo import ZoneInfo

try:
    from googleapiclient.discovery import build
except Exception:  # pragma: no cover - allow unit tests without google client installed
    build = None  # type: ignore

from app.config import settings
from app.connectors.google_auth import get_credentials


# -----------------------------
# Helpers
# -----------------------------
def _to_rfc3339_due(date_str: Optional[str], time_str: Optional[str]) -> Optional[str]:
    """
    Convert local date/time (YYYY-MM-DD, HH:MM) into RFC3339 UTC string for Google Tasks 'due'.
    If only date is provided, set due at local 23:59 of that day for a natural “due that day” feel.
    """
    if not date_str and not time_str:
        return None

    tz = ZoneInfo(settings.TIMEZONE)
    if date_str:
        year, month, day = map(int, date_str.split("-"))
    else:
        # if no date but time – assume today
        local_now = dt.datetime.now(tz)
        year, month, day = local_now.year, local_now.month, local_now.day

    if time_str:
        hh, mm = map(int, time_str.split(":"))
        local_dt = dt.datetime(year, month, day, hh, mm, tzinfo=tz)
    else:
        # end of the day
        local_dt = dt.datetime(year, month, day, 23, 59, tzinfo=tz)

    return local_dt.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _notes_with_location(notes: Optional[str], location: Optional[str]) -> Optional[str]:
    if location and notes:
        return f"{notes}\nLocation: {location}"
    if location:
        return f"Location: {location}"
    return notes


def _matches_criteria(task: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
    """
    Current supported hints:
      - title_hint: substring match on title (case-insensitive)
      - date_hint: ISO date "YYYY-MM-DD" expected (optional)
      - include_completed: bool (default False)
    """
    title_hint = (criteria or {}).get("title_hint")
    date_hint = (criteria or {}).get("date_hint")
    include_completed = (criteria or {}).get("include_completed", False)

    status = (task.get("status") or "").lower()
    if status == "completed" and not include_completed:
        return False

    if title_hint:
        if title_hint.lower() not in (task.get("title") or "").lower():
            return False

    if date_hint:
        due = task.get("due")
        if due:
            try:
                # RFC3339 → local date
                if due.endswith("Z"):
                    dt_utc = dt.datetime.fromisoformat(due.replace("Z", "+00:00"))
                else:
                    dt_utc = dt.datetime.fromisoformat(due)
                local = dt_utc.astimezone(ZoneInfo(settings.TIMEZONE)).date().isoformat()
                if local != date_hint:
                    return False
            except Exception:
                return False
        else:
            return False

    return True


# -----------------------------
# Connector
# -----------------------------
class GoogleTasksConnector:
    """
    Minimal wrapper around Google Tasks API.

    Usage:
      - Prefer injecting a ready-made service: GoogleTasksConnector(service=tasks_service)
      - Otherwise, this class will fetch credentials using google_auth.get_credentials and build one.

    Options:
      - tasklist_id: default '@default' (shows in your default Google Tasks list)
      - tasklist_name: if provided, will resolve (or create) a list with that name and use its id
    """

    SCOPES = ["https://www.googleapis.com/auth/tasks"]

    def __init__(self, service=None, logger=None, tasklist_id: str = "@default", tasklist_name: Optional[str] = None):
        self.logger = logger
        self._service = service
        self._tasklist_id_cache: Optional[str] = None
        self._default_tasklist_id = tasklist_id
        self._tasklist_name = tasklist_name

        if self._service is None and build is None:
            # google client not installed; allow app to boot and tests to run
            if self.logger:
                self.logger.warning("googleapiclient not installed; GoogleTasksConnector disabled.")

    # ---- service / credentials ----
    def _ensure_service(self):
        if self._service is not None:
            return self._service
        if build is None:
            raise NotImplementedError("Google Tasks client not available (googleapiclient missing).")
        creds = get_credentials(scopes=self.SCOPES)
        self._service = build("tasks", "v1", credentials=creds, cache_discovery=False)
        return self._service

    # ---- tasklist id ----
    def _get_tasklist_id(self) -> str:
        if self._tasklist_id_cache:
            return self._tasklist_id_cache

        # If explicitly using the default magic id, return it directly.
        if self._tasklist_name is None and self._default_tasklist_id == "@default":
            self._tasklist_id_cache = "@default"
            return self._tasklist_id_cache

        svc = self._ensure_service()

        # If a name is provided, resolve (or create) that list by title.
        if self._tasklist_name:
            name = self._tasklist_name
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

        # Otherwise use whatever id was configured (not '@default')
        self._tasklist_id_cache = self._default_tasklist_id
        return self._tasklist_id_cache

    # ---- public API ----
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        item: {"title", "date"?, "time"?, "notes"?, "location"?}
        """
        svc = self._ensure_service()
        tasklist_id = self._get_tasklist_id()
        body = {
            "title": item["title"],
            "notes": _notes_with_location(item.get("notes"), item.get("location")),
            "status": "needsAction",
        }
        due = _to_rfc3339_due(item.get("date"), item.get("time"))
        if due:
            body["due"] = due

        created = svc.tasks().insert(tasklist=tasklist_id, body=body).execute()
        return created

    def list(self, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        criteria: {"title_hint"?: str, "date_hint"?: "YYYY-MM-DD", "include_completed"?: bool}
        """
        svc = self._ensure_service()
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
        """
        Apply changes to matched tasks.
        changes can include: new_title, new_date, new_time, new_notes
        """
        svc = self._ensure_service()
        tasklist_id = self._get_tasklist_id()

        tasks = self.list(criteria)
        updated: List[Dict[str, Any]] = []
        for t in tasks:
            body = {"title": t.get("title"), "notes": t.get("notes"), "status": t.get("status")}
            if changes.get("new_title"):
                body["title"] = changes["new_title"]
            if "new_notes" in changes:
                body["notes"] = changes["new_notes"]
            # date/time
            if changes.get("new_date") or changes.get("new_time"):
                body["due"] = _to_rfc3339_due(changes.get("new_date"), changes.get("new_time"))
            # Perform patch
            res = svc.tasks().patch(tasklist=tasklist_id, task=t["id"], body=body).execute()
            updated.append(res)
        return updated

    def complete(self, criteria: Dict[str, Any]) -> int:
        """
        Mark all matched tasks as completed.
        """
        svc = self._ensure_service()
        tasklist_id = self._get_tasklist_id()

        tasks = self.list(criteria)
        count = 0
        for t in tasks:
            if (t.get("status") or "").lower() != "completed":
                body = {"status": "completed", "completed": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"}
                svc.tasks().patch(tasklist=tasklist_id, task=t["id"], body=body).execute()
                count += 1
        return count

    def delete(self, criteria: Dict[str, Any]) -> int:
        """
        Delete all matched tasks.
        """
        svc = self._ensure_service()
        tasklist_id = self._get_tasklist_id()

        tasks = self.list(criteria)
        count = 0
        for t in tasks:
            svc.tasks().delete(tasklist=tasklist_id, task=t["id"]).execute()
            count += 1
        return count
