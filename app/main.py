from fastapi import FastAPI, Request, Response
from twilio.twiml.messaging_response import MessagingResponse

from app.deps import build_connectors
from app.models import EventCreate, IntentResult
from app.utils.time_utils import normalize_event_datetimes
from app.services.confirmation_store import PendingStore
from app.services.scheduler import start_scheduler
from app.config import settings

app = FastAPI(title="WhatsApp GPT Assistant (Refactor with Updates & Tasks)")

intent, whisper, media, calendar, messenger, tasks, logger = build_connectors()
pending = PendingStore(ttl_min=settings.CONFIRM_TTL_MIN)

def twiml(text: str) -> Response:
    resp = MessagingResponse(); resp.message(text)
    return Response(content=str(resp), media_type="application/xml")

@app.get("/")
def health():
    return {"ok": True}

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
        start_iso = ev["start"].get("dateTime") or ev["start"].get("date","")
        summary = ev.get("summary","(no title)")
        lines.append(f"{i}. {summary} — {start_iso}")
    lines.append("Or reply '0' / 'cancel' to abort.")
    return "\n".join(lines)

@app.post("/whatsapp")
async def webhook(request: Request):
    form = await request.form()
    from_num = form.get("From", "")
    body = form.get("Body", "") or ""
    num_media = int(form.get("NumMedia", "0"))

    logger.info("Inbound: from=%s NumMedia=%s ctype=%s url=%s",
                from_num, num_media, form.get("MediaContentType0"), form.get("MediaUrl0"))

    # ---- Pending flows ----
    if pending.has(from_num):
        stash = pending.get(from_num)
        ptype = stash["type"]
        payload = stash["payload"]

        # Confirm creation
        if ptype == "create":
            if PendingStore.is_confirm(body):
                ev: EventCreate = payload["event"]
                link = calendar.create_event(ev)
                sdt, edt = normalize_event_datetimes(ev, settings.TIMEZONE)
                pending.pop(from_num)
                msg = ("✅ Event added to Google Calendar.\n"
                       f"🗓 {ev.title}\n"
                       f"🕑 {sdt.strftime('%A, %Y-%m-%d %H:%M')} – {edt.strftime('%H:%M')} ({settings.TIMEZONE})")
                if link: msg += f"\n📅 {link}"
                return twiml(msg)
            if PendingStore.is_cancel(body):
                pending.pop(from_num); return twiml("❎ Event discarded.")
            return twiml(payload["preview_text"])

        # Update: selection of candidate
        if ptype == "update_select":
            if PendingStore.is_cancel(body):
                pending.pop(from_num); return twiml("❎ Update cancelled.")
            choice = (body or "").strip()
            if choice.isdigit():
                idx = int(choice)
                cands = payload["candidates"]
                if 1 <= idx <= len(cands):
                    chosen = cands[idx-1]
                    # Move to confirm stage
                    pending.add(from_num, "update_confirm", {"event": chosen, "changes": payload["changes"]})
                    return twiml("Confirm update? Reply '1' / 'confirm' to apply, or '0' / 'cancel'.")
            # re-show
            return twiml(disambig_text(payload["candidates"]))

        # Update: confirm patch
        if ptype == "update_confirm":
            if PendingStore.is_confirm(body):
                ev = payload["event"]
                changes = payload["changes"]
                try:
                    updated = calendar.apply_update(ev, changes)
                    pending.pop(from_num)
                    title = updated.get("summary","(no title)")
                    start_iso = updated["start"].get("dateTime") or updated["start"].get("date","")
                    return twiml(f"✅ Updated: {title}\n🕑 {start_iso}")
                except Exception as e:
                    pending.pop(from_num)
                    return twiml(f"⚠️ Update failed: {e}")
            if PendingStore.is_cancel(body):
                pending.pop(from_num); return twiml("❎ Update cancelled.")
            return twiml("Reply '1' to apply update, or '0' to cancel.")

    # ---- Voice handling ----
    if num_media > 0:
        payload = media.fetch(form)
        transcript = whisper.transcribe(payload.bytes, filename=payload.filename).strip()
        if transcript:
            body = transcript
        else:
            return twiml("I received your voice note, but couldn’t transcribe it. Please try again?")

    if not body.strip():
        return twiml("Send a message or voice note 😊")

    # ---- Route intent ----
    result: IntentResult = intent.parse(body)
    # Confidence guardrails
    conf = result.confidence or 0.0

    # EVENT_CREATE (single)
    if result.intent == "EVENT_TASK" and result.event:
        pv = preview_text(result.event)
        pending.add(from_num, "create", {"event": result.event, "preview_text": pv})
        combined = (result.answer + "\n\n" if result.answer else "") + pv
        return twiml(combined)

    # EVENT_UPDATE
    if result.intent == "EVENT_UPDATE" and result.update:
        # Find candidates; if none, offer create?
        cands = calendar.find_candidates(result.update.criteria, window_days=7)
        if not cands:
            return twiml("I couldn't find a matching event to update. Want to create a new one instead?")
        if len(cands) == 1:
            # go to confirm
            pending.add(from_num, "update_confirm", {"event": cands[0], "changes": result.update.changes})
            return twiml("Found one match. Reply '1' / 'confirm' to apply the update, or '0' / 'cancel'.")
        # multiple → disambiguate
        pending.add(from_num, "update_select", {"candidates": cands, "changes": result.update.changes})
        return twiml(disambig_text(cands))

    # TASK_OP (skeleton using fallback connector)
    if result.intent == "TASK_OP" and result.task_op:
        op = result.task_op.op
        try:
            if op == "create" and result.task_op.tasks:
                ids = tasks.create(result.task_op.tasks)
                return twiml("✅ Tasks created:\n- " + "\n- ".join(ids))
            elif op == "list":
                items = tasks.list(result.task_op.criteria or {})
                return twiml("📝 Tasks:\n- " + "\n- ".join(items))
            elif op == "complete":
                msg = tasks.complete(result.task_op)
                return twiml("✅ " + msg)
            elif op == "delete":
                msg = tasks.delete(result.task_op)
                return twiml("🗑️ " + msg)
            elif op == "update":
                msg = tasks.update(result.task_op)
                return twiml("✏️ " + msg)
            else:
                return twiml("I parsed a task request, but details were missing. Please specify.")
        except NotImplementedError as e:
            return twiml(f"Tasks API not configured: {e}")

    # GENERAL_QA / CHITCHAT → respond
    return twiml(result.answer or f"Echo: {body}")

# ---- Daily digest (placeholder) ----
def daily_digest_job():
    try:
        messenger.send("🌅 Daily digest placeholder (wire your calendar summary here).")
    except Exception as e:
        logger.error("Daily digest error: %s", e)

scheduler = start_scheduler(daily_digest_job, hour=settings.DAILY_DIGEST_HOUR, minute=settings.DAILY_DIGEST_MINUTE)
