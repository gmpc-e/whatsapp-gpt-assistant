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
from app.utils.rate_limiter import rate_limiter
from app.utils.performance_monitor import perf_monitor


SYSTEM_PROMPT = (
    "You are an intent router for a WhatsApp assistant that handles calendar events, tasks, and general questions. "
    "Return ONLY strict JSON. The intents are: "
    "EVENT_TASK (create event), EVENT_UPDATE (modify existing event), TASK_OP (tasks), "
    "EVENT_LIST (list events), GENERAL_QA (general question), CHITCHAT (greeting/small talk).\n"
    "When EVENT_TASK, fill 'event'. When EVENT_UPDATE, fill 'update'. When TASK_OP, fill 'task_op'. "
    "When EVENT_LIST, fill 'list_query' with {scope:'day'|'week', date_hint?}.\n"
    "For EVENT_TASK: one event only.\n"
    "For EVENT_UPDATE: provide 'update' = {criteria:{who?,date_hint?,time_hint?,title_hint?}, "
    "changes:{new_title?,new_date?,new_time?,new_duration_minutes?,new_location?,new_notes?}}. "
    "Use AI-powered matching: extract person names, keywords from user text for criteria.\n"
    "For TASK_OP: op=create|update|list|complete|delete. For 'create', fill 'task' "
    "with {title, date?, time?, notes?, location?}. IMPORTANT: Parse natural language like "
    "'create a task, buy some milk' or 'task: buy milk' as op='create' with task.title='buy some milk'. "
    "For 'list', if no specific filter mentioned, show ALL tasks (don't add date filters). "
    "For 'update', fill 'task_update' with {criteria:{...}, changes:{...}}.\n"
    "Always set 'confidence' 0..1 and 'recency_required' if question needs fresh info.\n"
    f"Assume timezone {settings.TIMEZONE}. Resolve relative dates into the FUTURE and include YEAR when relevant."
)


class OpenAIIntentConnector:
    def __init__(self, openai_client, logger, debug: bool = False):
        self.client = openai_client
        self.logger = logger
        self.debug = debug

    @perf_monitor.monitor("openai_intent_parse")
    def parse(self, user_text: str) -> IntentResult:
        if not rate_limiter.is_allowed("openai_intent", settings.OPENAI_RATE_LIMIT_RPM, 60):
            wait_time = rate_limiter.wait_time("openai_intent", settings.OPENAI_RATE_LIMIT_RPM, 60)
            self.logger.warning("Rate limit exceeded, need to wait %.1f seconds", wait_time)
            return IntentResult(intent="GENERAL_QA", answer="I'm processing too many requests right now. Please try again in a moment.")
        
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

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=messages,
                timeout=30,
            )
            raw = completion.choices[0].message.content
        except Exception as e:
            self.logger.error("OpenAI API call failed: %s", e)
            return IntentResult(intent="GENERAL_QA", answer="I'm having trouble processing your request right now. Please try again in a moment.")
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

    @perf_monitor.monitor("openai_generate_answer")
    def generate_answer(
        self,
        user_text: str,
        domain: Optional[str] = None,
        recency_required: Optional[bool] = None,
    ) -> str:
        if not rate_limiter.is_allowed("openai_generate", settings.OPENAI_RATE_LIMIT_RPM, 60):
            wait_time = rate_limiter.wait_time("openai_generate", settings.OPENAI_RATE_LIMIT_RPM, 60)
            self.logger.warning("Rate limit exceeded for generation, need to wait %.1f seconds", wait_time)
            return "I'm processing too many requests right now. Please try again in a moment."
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

        try:
            completion = self.client.chat.completions.create(
                model=generation_model,
                messages=messages,
                temperature=0.7,
                timeout=30,
            )
            content = completion.choices[0].message.content or ""
        except Exception as e:
            self.logger.error("OpenAI generation failed: %s", e)
            return "I'm having trouble generating a response right now. Please try again in a moment."

        if self.debug:
            try:
                self.logger.info("[GPT] GenQnA <- %s", content)
            except Exception:
                pass

        return content.strip()
