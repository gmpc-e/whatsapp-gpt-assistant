# app/main.py
from __future__ import annotations

import datetime as dt
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.config import settings
from app.deps import build_connectors, PROJECT_ROOT, _resolve_path
from app.models import EventCreate, IntentResult, TaskItem, TaskUpdate
from app.services.confirmation_store import PendingStore
from app.services.scheduler import start_scheduler
from app.utils.time_utils import normalize_event_datetimes
from app.utils.validation import validate_phone_number, sanitize_text_input
from app.utils.config_validator import validate_configuration
from app.utils.performance_monitor import perf_monitor
from app.connectors.enhanced_nlp import EnhancedNLPProcessor

app = FastAPI(title="WhatsApp GPT Assistant")

config_validation = validate_configuration()
if not config_validation["valid"]:
    import sys
    print("Configuration validation failed. Check logs for details.")
    sys.exit(1)

# Build all connectors once
intent, whisper, media, calendar, tasks, messenger, logger = build_connectors()

# Pending multi-step interactions (create/confirm, update/select/confirm)
pending = PendingStore(ttl_min=settings.CONFIRM_TTL_MIN)

nlp_processor = EnhancedNLPProcessor()


def twiml(text: str) -> Response:
    resp = MessagingResponse()
    resp.message(text)
    return Response(content=str(resp), media_type="application/xml")


@app.get("/")
def health():
    return {"ok": True}

@app.get("/health")
def health_check():
    """Comprehensive health check for all connectors"""
    status = {"status": "healthy", "services": {}, "pending_confirmations": 0, "config_valid": True}
    
    try:
        config_check = validate_configuration()
        status["config_valid"] = config_check["valid"]
        if not config_check["valid"]:
            status["config_issues"] = config_check
    except Exception:
        status["config_valid"] = False
    
    try:
        test_result = intent.parse("test")
        status["services"]["intent"] = "ok" if test_result else "error"
    except Exception:
        status["services"]["intent"] = "error"
    
    try:
        from datetime import datetime, timedelta
        now = datetime.now()
        calendar.list_range(now, now + timedelta(hours=1))
        status["services"]["calendar"] = "ok"
    except Exception:
        status["services"]["calendar"] = "error"
    
    try:
        tasks.list({})
        status["services"]["tasks"] = "ok"
    except Exception:
        status["services"]["tasks"] = "error"
    
    try:
        stats = pending.get_stats()
        status["pending_confirmations"] = stats["total"]
        status["confirmation_breakdown"] = stats["by_type"]
    except Exception:
        status["pending_confirmations"] = "error"
    
    error_conditions = [
        any(s == "error" for s in status["services"].values()),
        not status["config_valid"],
        status["pending_confirmations"] == "error"
    ]
    
    if any(error_conditions):
        status["status"] = "degraded"
    
    return status


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
        "rate_limits": {
            "rpm": settings.OPENAI_RATE_LIMIT_RPM,
            "tpm": settings.OPENAI_RATE_LIMIT_TPM,
        },
        "connectors": {
            "intent": str(type(intent)),
            "calendar": str(type(calendar)),
            "tasks": str(type(tasks)),
            "whisper": str(type(whisper)),
            "media": str(type(media)),
        },
        "pending_store": pending.get_stats(),
        "performance": {
            "openai_intent": perf_monitor.get_stats("openai_intent_parse"),
            "openai_generate": perf_monitor.get_stats("openai_generate_answer"),
        }
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


@app.post("/whatsapp")
async def webhook(request: Request):
    try:
        form = await request.form()
        from_num = form.get("From", "")
        body = form.get("Body", "") or ""
        try:
            num_media = int(form.get("NumMedia", "0"))
        except (ValueError, TypeError):
            num_media = 0
        
        if not validate_phone_number(from_num):
            logger.warning("Invalid phone number format: %s", from_num)
            return twiml("Invalid phone number format.")
        
        body = sanitize_text_input(body)
        
    except Exception as e:
        logger.error("Failed to parse webhook request: %s", e)
        return twiml("Sorry, I couldn't process your message. Please try again.")

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
        if not stash:
            return twiml("Session expired. Please try again.")
        ptype = stash["type"]
        payload = stash["payload"]

        # Event create: confirm/cancel
        if ptype == "create":
            if PendingStore.is_confirm(body):
                ev: EventCreate = payload["event"]
                try:
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
                except Exception as e:
                    logger.error("Failed to create calendar event: %s", e)
                    pending.pop(from_num)
                    return twiml("❌ Sorry, I couldn't create the event. Please try again later.")
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

    # ---------- Voice handling ----------
    if num_media > 0:
        try:
            payload = media.fetch(form)
            transcript = whisper.transcribe(payload.bytes, filename=payload.filename).strip()
            if transcript:
                body = transcript
            else:
                return twiml("I received your voice note, but couldn't transcribe it. Please try again?")
        except Exception as e:
            logger.error("Voice transcription failed: %s", e)
            return twiml("Sorry, I couldn't process your voice message. Please try sending text instead.")

    if not body.strip():
        return twiml("Send a message or voice note 😊")

    # ---------- Route intent ----------
    try:
        result: IntentResult = intent.parse(body)
        intent_name = getattr(result, "intent", None) or "GENERAL_QA"
    except Exception as e:
        logger.error("Intent parsing failed: %s", e)
        return twiml("I'm having trouble understanding your message. Could you please rephrase it?")

    # ----- EVENT_TASK (create, with preview/confirm) -----
    if intent_name == "EVENT_TASK" and getattr(result, "event", None):
        if result.event:
            pv = preview_text(result.event)
            pending.add(from_num, "create", {"event": result.event, "preview_text": pv})
            combined = ((result.answer or "") + "\n\n" if result.answer else "") + pv
            return twiml(combined)

    # ----- EVENT_UPDATE (find → select? → confirm) -----
    if intent_name == "EVENT_UPDATE" and getattr(result, "update", None):
        if result.update and result.update.criteria:
            cands = calendar.find_candidates(result.update.criteria, window_days=7)
            if not cands:
                return twiml("I couldn't find a matching event to update. Want to create a new one instead?")
            if len(cands) == 1:
                pending.add(from_num, "update_confirm", {"event": cands[0], "changes": result.update.changes})
                return twiml("Found one match. Reply '1' / 'confirm' to apply the update, or '0' / 'cancel'.")
            pending.add(from_num, "update_select", {"candidates": cands, "changes": result.update.changes})
            return twiml(disambig_text(cands))

    # ----- EVENT_LIST (enhanced with NLP processing) -----
    if intent_name == "EVENT_LIST" and getattr(result, "list_query", None):
        try:
            start, end = nlp_processor.parse_date_range(body)
            events = calendar.list_range(start, end)
            
            if any(word in body.lower() for word in ['free', 'available', 'open', 'slot', 'beach', 'break']):
                free_slots = nlp_processor.find_free_slots(events, start, end, duration_hours=2)
                if free_slots:
                    lines = ["🏖️ Free time slots:"]
                    for slot in free_slots[:5]:
                        lines.append(f"• {slot['suggestion']}")
                    return twiml("\n".join(lines))
                else:
                    return twiml("😅 No significant free slots found in that period.")
            
            if any(word in body.lower() for word in ['summary', 'overview', 'statistics', 'stats']):
                period_name = "this period"
                if "next week" in body.lower():
                    period_name = "next week"
                elif "this week" in body.lower():
                    period_name = "this week"
                elif "tomorrow" in body.lower():
                    period_name = "tomorrow"
                
                try:
                    task_list = tasks.list({})
                    summary = nlp_processor.generate_summary(events, task_list, period_name)
                    return twiml(summary)
                except Exception:
                    # Fallback to events-only summary
                    summary = nlp_processor.generate_summary(events, [], period_name)
                    return twiml(summary)
            
            def _pretty_events(evts):
                if not evts:
                    return "📭 No events found."
                lines = ["🗓️ Events:"]
                for e in evts:
                    title = e.get("summary", "(no title)")
                    loc = e.get("location") or ""
                    desc = e.get("description") or ""
                    s = e.get("start", {})
                    start_iso = s.get("dateTime") or s.get("date")
                    when = "(no time)"
                    if start_iso:
                        if "T" in start_iso:
                            sdt = dt.datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(ZoneInfo(settings.TIMEZONE))
                            when = sdt.strftime("%a %Y-%m-%d %H:%M")
                        else:
                            when = f"{start_iso} (all-day)"
                    line = f"• {when} — {title}"
                    if loc:
                        line += f" @ {loc}"
                    if desc and len(desc) < 50:
                        line += f"\n   {desc}"
                    lines.append(line)
                return "\n".join(lines)

            return twiml(_pretty_events(events))
            
        except Exception as e:
            logger.error("Enhanced event listing failed: %s", e)
            return twiml("Sorry, I couldn't retrieve your events right now.")

    # ----- TASK_OP (Google Tasks) -----
    if intent_name == "TASK_OP" and getattr(result, "task_op", None) is not None:
        # Router may return string or object
        task_op_raw = result.task_op
        if isinstance(task_op_raw, str):
            op = task_op_raw.lower()
            criteria = {}
        elif task_op_raw:
            op = (task_op_raw.op or "").lower()
            criteria = task_op_raw.criteria or {}
        else:
            op = ""
            criteria = {}

        try:
            if op == "create":
                if hasattr(result, 'tasks') and getattr(result, 'tasks', None):
                    created_tasks = []
                    for task_data in result.tasks:
                        if isinstance(task_data, dict):
                            task_item = TaskItem(**task_data)
                            created = tasks.create(task_item.model_dump())
                            created_tasks.append(created.get('title', 'Untitled'))
                    if created_tasks:
                        return twiml(f"🧩 Created {len(created_tasks)} tasks: {', '.join(created_tasks)}")
                
                elif getattr(result, "task", None):
                    created = tasks.create(result.task.model_dump())
                    return twiml(f"🧩 Task created: {created.get('title')}")
                
                # Fallback: extract from raw OpenAI response
                elif hasattr(result, '_raw_data') and result._raw_data.get('tasks'):
                    created_tasks = []
                    for task_data in result._raw_data['tasks']:
                        if isinstance(task_data, dict) and 'title' in task_data:
                            task_item = TaskItem(**task_data)
                            created = tasks.create(task_item.model_dump())
                            created_tasks.append(created.get('title', 'Untitled'))
                    if created_tasks:
                        return twiml(f"🧩 Created {len(created_tasks)} tasks: {', '.join(created_tasks)}")

            elif op == "list":
                status_filter = nlp_processor.extract_task_status_filter(body)
                
                if not criteria:
                    criteria = {}
                
                if 'date_hint' in criteria and not any(word in body.lower() for word in ['today', 'tomorrow', 'this week', 'next week']):
                    del criteria['date_hint']
                
                items = tasks.list(criteria)
                
                if status_filter == "completed":
                    items = [t for t in items if t.get("status") == "completed"]
                elif status_filter == "open":
                    items = [t for t in items if t.get("status") != "completed"]
                
                if not items:
                    status_msg = f" {status_filter}" if status_filter and status_filter != "all" else ""
                    return twiml(f"📭 No{status_msg} tasks found.")
                
                if any(word in body.lower() for word in ['summary', 'overview', 'statistics', 'stats']):
                    summary = nlp_processor.generate_summary([], items, "your tasks")
                    return twiml(summary)
                
                tz = ZoneInfo(settings.TIMEZONE)
                status_label = f" {status_filter.title()}" if status_filter and status_filter != "all" else ""
                lines = [f"🧩{status_label} Tasks ({len(items)}):"]
                
                for t in items:
                    title = t.get("title", "(no title)")
                    status = t.get("status", "")
                    due = t.get("due")
                    
                    status_icon = "✅" if status == "completed" else "⏳"
                    
                    if due:
                        try:
                            if due.endswith("Z"):
                                d_utc = dt.datetime.fromisoformat(due.replace("Z", "+00:00"))
                            else:
                                d_utc = dt.datetime.fromisoformat(due)
                            local = d_utc.astimezone(tz)
                            due_s = local.strftime("%m/%d %H:%M")
                            lines.append(f"{status_icon} {title} — due {due_s}")
                        except Exception:
                            lines.append(f"{status_icon} {title} — due {due}")
                    else:
                        lines.append(f"{status_icon} {title}")
                
                return twiml("\n".join(lines))

            elif op == "complete":
                if getattr(result, "task_update", None):
                    count = tasks.complete(result.task_update.model_dump())
                    return twiml(f"✅ Completed {count} task(s).")
                else:
                    # Fallback: try to extract task title from natural language
                    if any(phrase in body.lower() for phrase in ['complete task', 'finish task', 'done task']):
                        text_lower = body.lower()
                        for pattern in ['complete task ', 'finish task ', 'done task ']:
                            if pattern in text_lower:
                                title_start = text_lower.find(pattern) + len(pattern)
                                title_hint = body[title_start:].strip()
                                if title_hint:
                                    try:
                                        task_update = TaskUpdate(
                                            criteria={"title_hint": title_hint},
                                            changes={}
                                        )
                                        count = tasks.complete(task_update.model_dump())
                                        return twiml(f"✅ Completed {count} task(s) matching '{title_hint}'.")
                                    except Exception as e:
                                        logger.error("Fallback task completion failed: %s", e)
                                break

            elif op == "delete" and getattr(result, "task_update", None):
                if result.task_update:
                    count = tasks.delete(result.task_update.model_dump())
                    return twiml(f"🗑️ Deleted {count} task(s).")

            elif op == "update" and getattr(result, "task_update", None):
                if result.task_update:
                    updated = tasks.update(
                        result.task_update.criteria or {}, result.task_update.changes or {}
                    )
                    return twiml(f"✏️ Updated {len(updated)} task(s).")

            else:
                hebrew_patterns = ['תוסיף משימה', 'משימה חדשה', 'הוסף משימה']
                english_patterns = ['create task', 'task:', 'new task', 'add task', 'create a task']
                
                if any(phrase in body.lower() for phrase in english_patterns) or any(phrase in body for phrase in hebrew_patterns):
                    title = None
                    
                    for pattern in ['תוסיף משימה,', 'תוסיף משימה -', 'תוסיף משימה חדשה -', 'משימה חדשה -', 'הוסף משימה:']:
                        if pattern in body:
                            start_idx = body.find(pattern) + len(pattern)
                            title = body[start_idx:].strip()
                            break
                    
                    if not title:
                        text_lower = body.lower()
                        patterns = [
                            'create a task,',
                            'create a task -',
                            'create task,',
                            'create task -',
                            'task:',
                            'new task:',
                            'add task:'
                        ]
                        
                        for pattern in patterns:
                            if pattern in text_lower:
                                title_start = text_lower.find(pattern) + len(pattern)
                                title = body[title_start:].strip()
                                break
                        
                        if not title:
                            for pattern in ['create task ', 'new task ', 'add task ', 'create a task ']:
                                if pattern in text_lower:
                                    title_start = text_lower.find(pattern) + len(pattern)
                                    title = body[title_start:].strip()
                                    break
                    
                    if title:
                        try:
                            task_item = TaskItem(title=title)
                            created = tasks.create(task_item.model_dump())
                            return twiml(f"🧩 Task created: {created.get('title')}")
                        except Exception as e:
                            logger.error("Fallback task creation failed: %s", e)
                
                hebrew_patterns = ['תוסיף משימה', 'משימה חדשה', 'הוסף משימה']
                english_patterns = ['create task', 'task:', 'new task', 'add task', 'create a task']
                
                if any(phrase in body.lower() for phrase in english_patterns) or any(phrase in body for phrase in hebrew_patterns):
                    title = None
                    
                    for pattern in ['תוסיף משימה,', 'תוסיף משימה -', 'תוסיף משימה חדשה -', 'משימה חדשה -', 'הוסף משימה:']:
                        if pattern in body:
                            start_idx = body.find(pattern) + len(pattern)
                            title = body[start_idx:].strip()
                            break
                    
                    if not title:
                        text_lower = body.lower()
                        patterns = [
                            'create a task,',
                            'create a task -',
                            'create task,',
                            'create task -',
                            'task:',
                            'new task:',
                            'add task:'
                        ]
                        
                        for pattern in patterns:
                            if pattern in text_lower:
                                title_start = text_lower.find(pattern) + len(pattern)
                                title = body[title_start:].strip()
                                break
                        
                        if not title:
                            for pattern in ['create task ', 'new task ', 'add task ', 'create a task ']:
                                if pattern in text_lower:
                                    title_start = text_lower.find(pattern) + len(pattern)
                                    title = body[title_start:].strip()
                                    break
                    
                    if title:
                        try:
                            task_item = TaskItem(title=title)
                            created = tasks.create(task_item.model_dump())
                            return twiml(f"🧩 Task created: {created.get('title')}")
                        except Exception as e:
                            logger.error("Fallback task creation failed: %s", e)
                            return twiml(f"⚠️ Failed to create task: {e}")
                
                if any(word in body.lower() for word in ['task', 'משימה']) and any(word in body.lower() for word in ['create', 'add', 'new', 'תוסיף', 'הוסף']):
                    words = body.split()
                    if len(words) > 2:
                        for i, word in enumerate(words):
                            if word.lower() in ['task', 'משימה'] and i < len(words) - 1:
                                title = ' '.join(words[i+1:]).strip('.,!?')
                                if title:
                                    try:
                                        task_item = TaskItem(title=title)
                                        created = tasks.create(task_item.model_dump())
                                        return twiml(f"🧩 Task created: {created.get('title')}")
                                    except Exception as e:
                                        logger.error("Final fallback task creation failed: %s", e)
                
                return twiml("🤔 I didn't get the task action. Try: create / list / complete / delete / update.")
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
