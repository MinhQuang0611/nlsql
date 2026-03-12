from __future__ import annotations

import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from graph.state import AgentState
from prompts.intent import INTENT_SYSTEM, INTENT_HUMAN

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

VALID_INTENTS = {"data_query", "chart_request", "schema_question", "greeting", "out_of_scope"}


async def intent_agent(state: AgentState) -> AgentState:
    user_query = state["user_query"]
    logger.info("[IntentAgent] query=%r", user_query)

    messages = [
        SystemMessage(content=INTENT_SYSTEM),
        HumanMessage(content=INTENT_HUMAN.format(user_query=user_query)),
    ]

    response = await _llm.ainvoke(messages)
    raw = response.content.strip()

    try:
        parsed = json.loads(raw)
        intent = parsed["intent"]
        reasoning = parsed.get("reasoning", "")

        if intent not in VALID_INTENTS:
            logger.warning("[IntentAgent] unknown intent %r — falling back to out_of_scope", intent)
            intent = "out_of_scope"

    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("[IntentAgent] parse error: %s | raw=%r", exc, raw)
        intent = "out_of_scope"
        reasoning = f"Parse error: {exc}"

    logger.info("[IntentAgent] intent=%s", intent)
    return {**state, "intent": intent, "intent_reasoning": reasoning}