"""
Một chỗ duy nhất khởi tạo ChatOpenAI cho mọi agent.

Trước đây mỗi agent tự gọi ChatOpenAI(model, temperature, api_key) — 9 chỗ, và
không chỗ nào truyền `llm_timeout` / `llm_max_tokens` dù config có khai báo.
Một request OpenAI treo sẽ giữ request HTTP vô hạn.
"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from config import get_settings

settings = get_settings()


def make_llm(model: str | None = None, temperature: float | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=model or settings.openai_model,
        temperature=settings.llm_temperature if temperature is None else temperature,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout,
        max_retries=2,
        max_tokens=settings.llm_max_tokens,
    )
