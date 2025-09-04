"""Enhanced OpenAI intent connector with better NLP capabilities."""

import datetime as dt
import json
import logging
from typing import Optional
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.models import (
    IntentResult,
    EventCreate,
    EventUpdate,
    EventUpdateChanges,
    EventUpdateCriteria,
    EventListQuery,
    TaskItem,
    TaskUpdate,
)
from app.config import settings
from app.utils.rate_limiter import rate_limiter
from app.utils.performance_monitor import perf_monitor


ENHANCED_SYSTEM_PROMPT = (
    "You are an advanced intent router for a WhatsApp assistant that handles calendar events, tasks, and general questions. "
    "Return ONLY strict JSON. The intents are: "
    "EVENT_TASK (create event), EVENT_UPDATE (modify existing event), TASK_OP (tasks), "
    "EVENT_LIST (list events, free slots, summaries), GENERAL_QA (general question), CHITCHAT (greeting/small talk).\n"
    
    "Enhanced Natural Language Understanding:\n"
    "- 'next week' = Monday to Sunday of next week\n"
    "- 'this week' = Monday to Sunday of current week\n"
    "- 'next Sunday' = the upcoming Sunday\n"
    "- 'tomorrow' = next day\n"
    "- 'free slots', 'available time', 'open slots' = EVENT_LIST with free time analysis\n"
    "- 'summary', 'overview', 'statistics' = EVENT_LIST with summary mode\n"
    "- 'open tasks', 'pending tasks' = TASK_OP list with status filter\n"
    "- 'completed tasks', 'done tasks' = TASK_OP list with completed filter\n"
    "- 'all tasks' = TASK_OP list with no filter\n"
    
    "When EVENT_TASK, fill 'event'. When EVENT_UPDATE, fill 'update'. When TASK_OP, fill 'task_op'. "
    "When EVENT_LIST, fill 'list_query' with scope (day/week) and date_hint if specific.\n"
    "For tasks: support 'create', 'list', 'update', 'complete', 'delete' operations.\n"
    "Always include 'answer' field with helpful response text."
)


class EnhancedOpenAIIntentConnector:
    """Enhanced OpenAI intent connector with better NLP."""
    
    def __init__(self, openai_client: OpenAI, logger: Optional[logging.Logger] = None, debug: bool = False):
        self.client = openai_client
        self.logger = logger or logging.getLogger(__name__)
        self.debug = debug

    @perf_monitor.monitor("enhanced_openai_intent_parse")
    def parse(self, user_text: str) -> IntentResult:
        if not rate_limiter.is_allowed("openai_intent", settings.OPENAI_RATE_LIMIT_RPM, 60):
            wait_time = rate_limiter.wait_time("openai_intent", settings.OPENAI_RATE_LIMIT_RPM, 60)
            self.logger.warning("Rate limit exceeded, need to wait %.1f seconds", wait_time)
            return IntentResult(intent="GENERAL_QA", answer="I'm processing too many requests right now. Please try again in a moment.")
        
        now_local = dt.datetime.now(ZoneInfo(settings.TIMEZONE))
        system_prompt = (
            ENHANCED_SYSTEM_PROMPT
            + f"\nCurrent local datetime: {now_local.isoformat()}"
            + "\nRules: Prefer future dates; if ambiguous ask for clarification in 'answer' but still set intent."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        if self.debug:
            try:
                self.logger.info("[GPT] Enhanced Router -> %s", json.dumps(messages, ensure_ascii=False))
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
            self.logger.error("Enhanced OpenAI API call failed: %s", e)
            return IntentResult(intent="GENERAL_QA", answer="I'm having trouble processing your request right now. Please try again in a moment.")
        
        if self.debug:
            try:
                self.logger.info("[GPT] Enhanced Router <- %s", raw)
            except Exception:
                pass

        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError as e:
            self.logger.error("Enhanced JSON decode error: %s", e)
            return IntentResult(intent="GENERAL_QA", answer="I had trouble understanding that. Could you rephrase?")

        intent_name = data.get("intent", "GENERAL_QA")
        
        result = IntentResult(
            intent=intent_name,
            confidence=data.get("confidence", 0.8),
            answer=data.get("answer", "")
        )

        if intent_name == "EVENT_TASK" and "event" in data:
            try:
                result.event = EventCreate(**data["event"])
            except Exception as e:
                self.logger.warning("Enhanced event parsing failed: %s", e)
                result.intent = "GENERAL_QA"
                result.answer = "I had trouble understanding the event details. Could you be more specific?"

        elif intent_name == "EVENT_UPDATE" and "update" in data:
            try:
                update_data = data["update"]
                criteria = EventUpdateCriteria(**update_data.get("criteria", {}))
                changes = EventUpdateChanges(**update_data.get("changes", {}))
                result.update = EventUpdate(criteria=criteria, changes=changes)
            except Exception as e:
                self.logger.warning("Enhanced update parsing failed: %s", e)
                result.intent = "GENERAL_QA"
                result.answer = "I had trouble understanding what you want to update. Could you be more specific?"

        elif intent_name == "EVENT_LIST" and "list_query" in data:
            try:
                result.list_query = EventListQuery(**data["list_query"])
            except Exception as e:
                self.logger.warning("Enhanced list query parsing failed: %s", e)
                result.list_query = EventListQuery(scope="day")

        elif intent_name == "TASK_OP":
            if "task_op" in data:
                task_op_data = data["task_op"]
                if isinstance(task_op_data, str):
                    result.task_op = task_op_data
                else:
                    result.task_op = TaskUpdate(**task_op_data)
            
            if "task" in data:
                try:
                    result.task = TaskItem(**data["task"])
                except Exception as e:
                    self.logger.warning("Enhanced task parsing failed: %s", e)
            
            if "task_update" in data:
                try:
                    result.task_update = TaskUpdate(**data["task_update"])
                except Exception as e:
                    self.logger.warning("Enhanced task update parsing failed: %s", e)

        return result

    @perf_monitor.monitor("enhanced_openai_generate_answer")
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
        
        generation_model = "gpt-4o-mini"
        
        system_content = (
            "You are a helpful WhatsApp assistant. Provide concise, friendly responses. "
            "Keep responses under 300 characters when possible. Use emojis appropriately. "
            "If you don't know something, say so honestly."
        )
        
        if domain:
            system_content += f" Focus on {domain} topics."
        if recency_required:
            system_content += " Prioritize recent/current information."

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_text}
        ]

        if self.debug:
            try:
                self.logger.info("[GPT] Enhanced Generation -> %s", json.dumps(messages, ensure_ascii=False))
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
            self.logger.error("Enhanced OpenAI generation failed: %s", e)
            return "I'm having trouble generating a response right now. Please try again in a moment."

        if self.debug:
            try:
                self.logger.info("[GPT] Enhanced Generation <- %s", content)
            except Exception:
                pass

        return content
