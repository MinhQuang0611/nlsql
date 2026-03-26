from __future__ import annotations

import logging
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

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

class IntentClassifierSchema(BaseModel):
    intent: str = Field(description='Ý định của người dùng: "greeting", "data_query", "chart_request", "schema_question", "out_of_scope", hoặc "ambiguous".')
    reasoning: str = Field(description='Lý do phân loại ý định này.')
    clarification_question: Optional[str] = Field(default=None, description='Nếu intent là "ambiguous", vui lòng đặt câu hỏi ở đây để làm rõ.')

VALID_INTENTS = {"data_query", "chart_request", "schema_question", "greeting", "out_of_scope", "ambiguous"}

async def intent_agent(state: AgentState) -> AgentState:
    user_query = state.get("user_query", "")
    logger.info("[IntentAgent] query=%r", user_query)

    messages = [
        SystemMessage(content=INTENT_SYSTEM),
        HumanMessage(content=INTENT_HUMAN.format(user_query=user_query)),
    ]

    llm_structured = _llm.with_structured_output(IntentClassifierSchema)
    
    clarification_question: str | None = None
    intent = "out_of_scope"
    reasoning = ""

    try:
        response = await llm_structured.ainvoke(messages)
        intent = response.intent
        reasoning = response.reasoning
        clarification_question = response.clarification_question

        if intent not in VALID_INTENTS:
            logger.warning("[IntentAgent] unknown intent %r — falling back to out_of_scope", intent)
            intent = "out_of_scope"
            
    except Exception as exc:
        logger.error("[IntentAgent] parsed error: %s", exc, exc_info=True)
        intent = "out_of_scope"
        reasoning = f"Parse error: {exc}"

    logger.info("[IntentAgent] intent=%s", intent)
    return {**state, "intent": intent, "intent_reasoning": reasoning, "clarification_question": clarification_question}