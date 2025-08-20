import json
import datetime as dt
from zoneinfo import ZoneInfo

from app.models import IntentResult, EventCreate, EventUpdate, TaskOp
from app.config import settings

SYSTEM_PROMPT = (
    "You are an intent router for a WhatsApp assistant. "
    "Return ONLY strict JSON. The intents are: "
    "EVENT_TASK (create event), EVENT_UPDATE (modify existing event), TASK_OP (tasks), "
    "GENERAL_QA (general question), CHITCHAT (greeting/small talk).\n"
    "When EVENT_TASK, fill 'event'. When EVENT_UPDATE, fill 'update'. When TASK_OP, fill 'task_op'.\n"
    "For EVENT_TASK: one event. (Multi-event may come later.)\n"
    "For EVENT_UPDATE: provide 'criteria' (who/date_hint/time_hint/title_hint) and 'changes' "
    "(new_title/new_date/new_time/new_duration_minutes/new_location/new_notes).\n"
    "For TASK_OP: op=create|update|list|complete|delete; include tasks[] when applicable.\n"
    "Always set 'confidence' 0..1 and 'recency_required' if question seems to need fresh info.\n"
    "Assume timezone %s. Resolve relative dates into the FUTURE and include YEAR when relevant."
) % settings.TIMEZONE

class OpenAIIntentConnector:
    def __init__(self, openai_client, logger, debug: bool = False):
        self.client = openai_client
        self.logger = logger
        self.debug = debug

    def parse(self, user_text: str) -> IntentResult:
        now_local = dt.datetime.now(ZoneInfo(settings.TIMEZONE))
        system_prompt = (
            SYSTEM_PROMPT
            + f"\nCurrent local datetime: {now_local.isoformat()}"
            + "\nRules: Prefer future dates; if ambiguous ask for clarification in 'answer' but still set intent."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]
        if self.debug:
            self.logger.info("[GPT] Router -> %s", json.dumps(messages, ensure_ascii=False))

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = completion.choices[0].message.content
        if self.debug:
            self.logger.info("[GPT] Router <- %s", raw)

        # Best-effort parse
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return IntentResult(intent="QUESTION", answer=raw or "OK")

        # Map GENERAL_QA to QUESTION for compatibility
        intent = data.get("intent","QUESTION")
        if intent == "GENERAL_QA":
            intent = "QUESTION"

        result = IntentResult(
            intent=intent,
            answer=data.get("answer",""),
            confidence=data.get("confidence", None),
            recency_required=data.get("recency_required", None),
            domain=data.get("domain", None),
        )

        if data.get("event"):
            try:
                result.event = EventCreate(**data["event"])
            except Exception:
                pass
        if data.get("update"):
            try:
                result.update = EventUpdate(**data["update"])
            except Exception:
                pass
        if data.get("task_op"):
            try:
                result.task_op = TaskOp(**data["task_op"])
            except Exception:
                pass

        return result
