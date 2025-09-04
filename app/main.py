# app/main.py
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.deps import build_connectors, PROJECT_ROOT, _resolve_path
from app.models import EventCreate, IntentResult
from app.services.confirmation_store import PendingStore
from app.services.scheduler import start_scheduler
from app.utils.time_utils import normalize_event_datetimes

app = FastAPI(title="WhatsApp GPT Assistant")

# Build all connectors once
intent, whisper, media, calendar, tasks, messenger, logger = build_connectors()

# Pending multi-step interactions (create/confirm, update/select/confirm)
pending = PendingStore(ttl_min=settings.CONFIRM_TTL_MIN)


def twiml(text: str) -> Response:
    resp = MessagingResponse()
    resp.message(text)
    return Response(content=str(resp), media_type="application/xml")


@app.get("/")
def health():
    return {"ok": True}


@app.get("/debug")
def debug():
    return {
        "cwd": str(Path.cwd()),
        "project_root": str(PROJECT_ROOT),
        "GOOGLE_CREDENTIALS_FILE": settings.GOOGLE_CREDENTIALS_FILE,
        "GOOGLE_TOKEN_FILE": settings.GOOGLE_TOKEN_FILE,
        "resolved_credentials": str(_resolve_path(settings.GOOGLE_CREDENTIALS_FILE)),
        "resolved_token": str(_resolve_path(settings.GOOGLE_TOKEN_FILE)),
        "timezone": settings.TIMEZONE,
        "env_loaded": True,
    }


def preview_text(ev: EventCreate) -> str:
    sdt, edt = normalize_event_datetimes(ev, settings.TIMEZONE)
    loc = ev.location or "—"
    notes = ev.notes or "—"
    return (
        "Please confirm this event:\n"
        f"• Title: {ev.title}\n"
        f"• When: {sdt.strftime('%A, %Y-%m-%d %H:%M')} – {edt.strftime('%H:%M')} ({settings.TIMEZONE})\n"
        f"• Location: {loc}\n"
        f"• Notes: {notes}\n\n"
        "Reply '1' / 'confirm' to add, or '0' / 'cancel' to discard."
    )


def disambig_text(cands):
    lines = ["I found multiple matches. Reply with a number:"]
    for i, ev in enumerate(cands, start=1):
        start_iso = ev["start"].get("dateTime") or ev["start"].get("date", "")
        summary = ev.get("summary", "(no title)")
        lines.append(f"{i}. {summary} — {start_iso}")
    lines.append("Or reply '0' / 'cancel' to abort.")
    return "\n".join(lines)


def task_list_disambig_text(lists):
    lines = ["I found multiple task lists. Reply with a number:"]
    for i, lst in enumerate(lists, start=1):
        title = lst.get("title", "(no title)")
        lines.append(f"{i}. {title}")
    lines.append("Or reply '0' / 'cancel' to abort.")
    return "\n".join(lines)


@app.post("/whatsapp")
async def webhook(request: Request):
    form = await request.form()
    from_num = form.get("From", "")
    body = form.get("Body", "") or ""
    num_media = int(form.get("NumMedia", "0"))

    logger.info(
        "Inbound: from=%s NumMedia=%s ctype=%s url=%s",
        from_num,
        num_media,
        form.get("MediaContentType0"),
        form.get("MediaUrl0"),
    )

    # ---------- Pending multi-step flows ----------
    if pending.has(from_num):
        stash = pending.get(from_num)
        ptype = stash["type"]
        payload = stash["payload"]

        # Event create: confirm/cancel
        if ptype == "create":
            if PendingStore.is_confirm(body):
                ev: EventCreate = payload["event"]
                link = calendar.create_event(ev)
                sdt, edt = normalize_event_datetimes(ev, settings.TIMEZONE)
                pending.pop(from_num)
                msg = (
                    "✅ Event added to Google Calendar.\n"
                    f"🗓 {ev.title}\n"
                    f"🕑 {sdt.strftime('%A, %Y-%m-%d %H:%M')} – {edt.strftime('%H:%M')} ({settings.TIMEZONE})"
                )
                if link:
                    msg += f"\n📅 {link}"
                return twiml(msg)
            if PendingStore.is_cancel(body):
                pending.pop(from_num)
                return twiml("❎ Event discarded.")
            # re-show preview
            return twiml(payload["preview_text"])

        # Event update: user chooses which candidate
        if ptype == "update_select":
            if PendingStore.is_cancel(body):
                pending.pop(from_num)
                return twiml("❎ Update cancelled.")
            choice = (body or "").strip()
            if choice.isdigit():
                idx = int(choice)
                cands = payload["candidates"]
                if 1 <= idx <= len(cands):
                    chosen = cands[idx - 1]
                    pending.add(
                        from_num,
                        "update_confirm",
                        {"event": chosen, "changes": payload["changes"]},
                    )
                    return twiml("Confirm update? Reply '1' / 'confirm' to apply, or '0' / 'cancel'.")
            return twiml(disambig_text(payload["candidates"]))

        # Event update: confirm patch
        if ptype == "update_confirm":
            if PendingStore.is_confirm(body):
                ev = payload["event"]
                changes = payload["changes"]
                try:
                    updated = calendar.apply_update(ev, changes)
                    pending.pop(from_num)
                    title = updated.get("summary", "(no title)")
                    start_iso = updated["start"].get("dateTime") or updated["start"].get("date", "")
                    return twiml(f"✅ Updated: {title}\n🕑 {start_iso}")
                except Exception as e:
                    pending.pop(from_num)
                    return twiml(f"⚠️ Update failed: {e}")
            if PendingStore.is_cancel(body):
                pending.pop(from_num)
                return twiml("❎ Update cancelled.")
            return twiml("Reply '1' to apply update, or '0' to cancel.")

        if ptype == "task_list_select":
            if PendingStore.is_cancel(body):
                pending.pop(from_num)
                return twiml("❎ Task creation cancelled.")
            choice = (body or "").strip()
            if choice.isdigit():
                idx = int(choice)
                matching_lists = payload["matching_lists"]
                if 1 <= idx <= len(matching_lists):
                    chosen_list = matching_lists[idx - 1]
                    task_data = payload["task_data"]
                    created = tasks.create(task_data, chosen_list["id"])
                    pending.pop(from_num)
                    return twiml(f"🧩 Task created in '{chosen_list['title']}': {created.get('title')}")
            return twiml(task_list_disambig_text(payload["matching_lists"]))

    # ---------- Voice handling ----------
    if num_media > 0:
        payload = media.fetch(form)
        transcript = whisper.transcribe(payload.bytes, filename=payload.filename).strip()
        if transcript:
            body = transcript
        else:
            return twiml("I received your voice note, but couldn’t transcribe it. Please try again?")

    if not body.strip():
        return twiml("Send a message or voice note 😊")

    # ---------- Route intent ----------
    result: IntentResult = intent.parse(body)
    intent_name = getattr(result, "intent", None) or "GENERAL_QA"

    # ----- EVENT_TASK (create, with preview/confirm) -----
    if intent_name == "EVENT_TASK" and getattr(result, "event", None):
        pv = preview_text(result.event)
        pending.add(from_num, "create", {"event": result.event, "preview_text": pv})
        combined = ((result.answer or "") + "\n\n" if result.answer else "") + pv
        return twiml(combined)

    # ----- EVENT_UPDATE (find → select? → confirm) -----
    if intent_name == "EVENT_UPDATE" and getattr(result, "update", None):
        cands = calendar.find_candidates(result.update.criteria, window_days=7)
        if not cands:
            return twiml("I couldn't find a matching event to update. Want to create a new one instead?")
        if len(cands) == 1:
            pending.add(from_num, "update_confirm", {"event": cands[0], "changes": result.update.changes})
            return twiml("Found one match. Reply '1' / 'confirm' to apply the update, or '0' / 'cancel'.")
        pending.add(from_num, "update_select", {"candidates": cands, "changes": result.update.changes})
        return twiml(disambig_text(cands))

    # ----- EVENT_LIST (day/week pretty print) -----
    if intent_name == "EVENT_LIST" and getattr(result, "list_query", None):
        tz = ZoneInfo(settings.TIMEZONE)
        today = dt.datetime.now(tz).date()

        def _resolve_range(q):
            d = today
            if q.date_hint:
                try:
                    d = dt.date.fromisoformat(q.date_hint)
                except Exception:
                    pass
            if q.scope == "day":
                start = dt.datetime(d.year, d.month, d.day, 0, 0, tzinfo=tz)
                end = start + dt.timedelta(days=1)
            else:
                monday = d - dt.timedelta(days=d.weekday())
                start = dt.datetime(monday.year, monday.month, monday.day, 0, 0, tzinfo=tz)
                end = start + dt.timedelta(days=7)
            return start, end

        start, end = _resolve_range(result.list_query)

        try:
            events = calendar.list_range(start, end)
        except NotImplementedError:
            return twiml("Listing is not configured yet.")

        def _pretty_events(evts):
            if not evts:
                return "📭 No events."
            lines = ["🗓️ Upcoming:"]
            for e in evts:
                title = e.get("summary", "(no title)")
                loc = e.get("location") or ""
                desc = e.get("description") or ""
                s = e.get("start", {})
                start_iso = s.get("dateTime") or s.get("date")
                when = "(no time)"
                if start_iso:
                    if "T" in start_iso:
                        sdt = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(tz)
                        when = sdt.strftime("%a %Y-%m-%d %H:%M")
                    else:
                        when = f"{start_iso} (all-day)"
                line = f"• {when} — {title}"
                if loc:
                    line += f" @ {loc}"
                if desc:
                    line += f"\n   {desc}"
                lines.append(line)
            return "\n".join(lines)

        return twiml(_pretty_events(events))

    # ----- TASK_OP (Google Tasks) -----
    if intent_name == "TASK_OP" and getattr(result, "task_op", None) is not None:
        # Router may return string or object
        task_op_raw = result.task_op
        if isinstance(task_op_raw, str):
            op = task_op_raw.lower()
            criteria = {}
        else:
            op = (task_op_raw.op or "").lower()
            criteria = task_op_raw.criteria or {}

        try:
            if op == "create" and getattr(result, "task", None):
                task_data = result.task.model_dump()
                list_hint = task_data.get("list_hint")
                
                if list_hint:
                    matching_lists = tasks.find_best_matching_list(list_hint)
                    if not matching_lists:
                        return twiml(f"🧩 I couldn't find a task list matching '{list_hint}'. Creating task in default list.")
                    elif len(matching_lists) == 1:
                        created = tasks.create(task_data, matching_lists[0]["id"])
                        return twiml(f"🧩 Task created in '{matching_lists[0]['title']}': {created.get('title')}")
                    else:
                        pending.add(from_num, "task_list_select", {
                            "task_data": task_data, 
                            "matching_lists": matching_lists
                        })
                        return twiml(task_list_disambig_text(matching_lists))
                else:
                    created = tasks.create(task_data)
                    return twiml(f"🧩 Task created: {created.get('title')}")

            elif op == "list":
                if not criteria:
                    criteria = {"date_hint": "tomorrow"}
                items = tasks.list(criteria)
                if not items:
                    return twiml("📭 No tasks found.")
                tz = ZoneInfo(settings.TIMEZONE)
                lines = ["🧩 Tasks:"]
                for t in items:
                    title = t.get("title", "(no title)")
                    due = t.get("due")
                    if due:
                        try:
                            # RFC3339 → local
                            if due.endswith("Z"):
                                d_utc = dt.datetime.fromisoformat(due.replace("Z", "+00:00"))
                            else:
                                d_utc = dt.datetime.fromisoformat(due)
                            local = d_utc.astimezone(tz)
                            due_s = local.strftime("%Y-%m-%d %H:%M")
                        except Exception:
                            due_s = due
                        lines.append(f"• {title} — due {due_s}")
                    else:
                        lines.append(f"• {title}")
                return twiml("\n".join(lines))

            elif op == "complete" and getattr(result, "task_update", None):
                count = tasks.complete(result.task_update.model_dump())
                return twiml(f"✅ Completed {count} task(s).")

            elif op == "delete" and getattr(result, "task_update", None):
                count = tasks.delete(result.task_update.model_dump())
                return twiml(f"🗑️ Deleted {count} task(s).")

            elif op == "update" and getattr(result, "task_update", None):
                updated = tasks.update(
                    result.task_update.criteria or {}, result.task_update.changes or {}
                )
                return twiml(f"✏️ Updated {len(updated)} task(s).")

            else:
                return twiml("🤔 I didn’t get the task action. Try: create / list / complete / delete / update.")
        except Exception as e:
            logger.exception("TASK_OP failed")
            return twiml(f"⚠️ Task error: {e}")

    # ----- GENERAL_QA / CHITCHAT -----
    if intent_name in ("GENERAL_QA", "QUESTION", "CHITCHAT"):
        if hasattr(intent, "generate_answer"):
            rich = intent.generate_answer(
                body,
                domain=getattr(result, "domain", None),
                recency_required=getattr(result, "recency_required", None),
            )
            return twiml(rich or (result.answer or f"Echo: {body}"))
        return twiml(result.answer or f"Echo: {body}")

    # Fallback
    return twiml("I’m not sure I got that—try again?")


# ---------- Daily digest (placeholder) ----------
def daily_digest_job():
    try:
        messenger.send("🌅 Daily digest placeholder (wire your calendar summary here).")
    except Exception as e:
        logger.error("Daily digest error: %s", e)


# Start scheduler (no-op in tests)
scheduler = start_scheduler(
    daily_digest_job, hour=settings.DAILY_DIGEST_HOUR, minute=settings.DAILY_DIGEST_MINUTE
)
