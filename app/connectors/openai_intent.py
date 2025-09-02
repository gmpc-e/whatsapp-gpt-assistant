import json
import datetime as dt
from zoneinfo import ZoneInfo
from typing import Optional

from app.models import (
    IntentResult,
    EventCreate,
    EventUpdate,
    TaskOp,
    EventListQuery,
    TaskItem,
    TaskUpdate,
)
from app.config import settings


SYSTEM_PROMPT = (
    "You are an intent router for a WhatsApp assistant. "
    "Return ONLY strict JSON. The intents are: "
    "EVENT_TASK (create event), EVENT_UPDATE (modify existing event), TASK_OP (tasks), "
    "EVENT_LIST (list events), GENERAL_QA (general question), CHITCHAT (greeting/small talk).\n"
    "When EVENT_TASK, fill 'event'. When EVENT_UPDATE, fill 'update'. When TASK_OP, fill 'task_op'. "
    "When EVENT_LIST, fill 'list_query' with {scope:'day'|'week', date_hint?}.\n"
    "For EVENT_TASK: one event only.\n"
    "For EVENT_UPDATE: provide 'update' = {criteria:{who?,date_hint?,time_hint?,title_hint?}, "
    "changes:{new_title?,new_date?,new_time?,new_duration_minutes?,new_location?,new_notes?}}.\n"
    "For TASK_OP: op=create|update|list|complete|delete. For 'create', fill 'task' "
    "with {title, date?, time?, notes?, location?}. For 'update', fill 'task_update' with "
    "{criteria:{...}, changes:{...}}.\n"
    "Always set 'confidence' 0..1 and 'recency_required' if question needs fresh info.\n"
    f"Assume timezone {settings.TIMEZONE}. Resolve relative dates into the FUTURE and include YEAR when relevant."
)


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
            try:
                self.logger.info("[GPT] Router -> %s", json.dumps(messages, ensure_ascii=False))
            except Exception:
                pass

        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=messages,
        )
        raw = completion.choices[0].message.content
        if self.debug:
            try:
                self.logger.info("[GPT] Router <- %s", raw)
            except Exception:
                pass

        # Best-effort parse
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # fall back to a generic Q&A envelope
            return IntentResult(intent="QUESTION", answer=raw or "OK")

        # Map GENERAL_QA to QUESTION for compatibility
        intent = data.get("intent", "QUESTION")
        if intent == "GENERAL_QA":
            intent = "QUESTION"

        result = IntentResult(
            intent=intent,
            answer=data.get("answer", ""),
            confidence=data.get("confidence", None),
            recency_required=data.get("recency_required", None),
            domain=data.get("domain", None),
        )

        # payloads
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
        if data.get("list_query"):
            try:
                result.list_query = EventListQuery(**data["list_query"])
            except Exception:
                pass
        if data.get("task"):
            try:
                result.task = TaskItem(**data["task"])
            except Exception:
                pass
        if data.get("task_update"):
            try:
                result.task_update = TaskUpdate(**data["task_update"])
            except Exception:
                pass

        return result

    def generate_answer(
        self,
        user_text: str,
        domain: Optional[str] = None,
        recency_required: Optional[bool] = None,
    ) -> str:
        """
        High-quality general Q&A answer (WhatsApp-friendly).
        Uses a stronger prompt than the router and can switch models later if needed.
        """
        system = (
            "You are a helpful, concise assistant chatting on WhatsApp. "
            "Answer clearly in short paragraphs or up to ~7 bullets. "
            "Avoid walls of text. If it helps, offer ONE smart follow-up question at the end."
        )
        if domain:
            system += f" Domain hint: {domain}."

        generation_model = "gpt-4o-mini"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text},
        ]

        if self.debug:
            try:
                self.logger.info("[GPT] GenQnA -> %s", user_text)
            except Exception:
                pass

        completion = self.client.chat.completions.create(
            model=generation_model,
            messages=messages,
            temperature=0.7,
        )
        content = completion.choices[0].message.content or ""

        if self.debug:
            try:
                self.logger.info("[GPT] GenQnA <- %s", content)
            except Exception:
                pass

        return content.strip()
