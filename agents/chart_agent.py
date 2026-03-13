from __future__ import annotations

import json
import logging
from typing import Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from graph.state import AgentState, ChartConfig
from prompts.chart import CHART_SYSTEM, CHART_HUMAN, CHART_HUMAN_FORCED
from utils.data_profiler import profile_columns, format_profile_for_prompt
from utils.chart_adjustment import adjust_chart_data

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

VALID_CHART_TYPES = {"bar", "line", "pie", "table", "number", "scatter"}


def _reshape_for_chart(
    rows: list[dict[str, Any]],
    config: ChartConfig,
) -> list[dict[str, Any]]:

    if config["chart_type"] == "number":
        return rows[:1]

    reshaped = []
    for row in rows:
        point: dict[str, Any] = {}
        if config.get("x_axis") and config["x_axis"] in row:
            point["x"] = str(row[config["x_axis"]])
        if config.get("y_axis") and config["y_axis"] in row:
            point["y"] = row[config["y_axis"]]
        if config.get("group_by") and config["group_by"] in row:
            point["group"] = str(row[config["group_by"]])
        point.update({k: v for k, v in row.items() if k not in point})
        reshaped.append(point)

    return reshaped


def _parse_llm_response(raw: str, user_query: str) -> ChartConfig:
    """Parse LLM JSON response thành ChartConfig, fallback về table nếu lỗi."""
    try:
        parsed = json.loads(raw)
        chart_type = parsed.get("chart_type", "table")
        if chart_type not in VALID_CHART_TYPES:
            chart_type = "table"

        return ChartConfig(
            chart_type=chart_type,
            x_axis=parsed.get("x_axis"),
            y_axis=parsed.get("y_axis"),
            group_by=parsed.get("group_by"),
            title=parsed.get("title", user_query[:60]),
            x_label=parsed.get("x_label"),
            y_label=parsed.get("y_label"),
        )
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("[ChartAgent] parse error: %s", exc)
        return ChartConfig(
            chart_type="table",
            x_axis=None, y_axis=None, group_by=None,
            title=user_query[:60], x_label=None, y_label=None,
        )


async def run_chart_agent(
    user_query: str,
    query_result: list[dict[str, Any]],
    forced_chart_type: Optional[str] = None,
) -> tuple[ChartConfig, list[dict[str, Any]], list[dict[str, Any]]]:
    """

    Args:
        user_query: Câu hỏi của người dùng
        query_result: Data thô từ database
        forced_chart_type: Nếu có, ép agent dùng loại chart này

    Returns:
        (chart_config, chart_data, column_profiles)
    """
    if not query_result:
        logger.warning("[ChartAgent] empty query_result — defaulting to table")
        chart_config = ChartConfig(
            chart_type="table",
            x_axis=None, y_axis=None, group_by=None,
            title=user_query[:60], x_label=None, y_label=None,
        )
        return chart_config, [], []

    if forced_chart_type and forced_chart_type not in VALID_CHART_TYPES:
        logger.warning("[ChartAgent] invalid forced_chart_type=%s, ignoring", forced_chart_type)
        forced_chart_type = None

    profiles = profile_columns(query_result)
    column_profile_text = format_profile_for_prompt(profiles)

    columns = list(query_result[0].keys())
    sample_rows = query_result[:3]

    logger.info(
        "[ChartAgent] columns=%s, rows=%d, forced_chart_type=%s",
        columns, len(query_result), forced_chart_type,
    )
    logger.info("[ChartAgent] column_profiles:\n%s", column_profile_text)

    if forced_chart_type:
        human_content = CHART_HUMAN_FORCED.format(
            user_query=user_query,
            columns=columns,
            column_profile=column_profile_text,
            sample_rows=sample_rows,
            forced_chart_type=forced_chart_type,
        )
    else:
        human_content = CHART_HUMAN.format(
            user_query=user_query,
            columns=columns,
            column_profile=column_profile_text,
            sample_rows=sample_rows,
        )

    messages = [
        SystemMessage(content=CHART_SYSTEM),
        HumanMessage(content=human_content),
    ]

    response = await _llm.ainvoke(messages)
    raw = response.content.strip()

    chart_config = _parse_llm_response(raw, user_query)
    if forced_chart_type and chart_config["chart_type"] != forced_chart_type:
        logger.warning(
            "[ChartAgent] LLM returned chart_type=%s but forced=%s, overriding",
            chart_config["chart_type"], forced_chart_type,
        )
        chart_config["chart_type"] = forced_chart_type  # type: ignore[literal-required]

    chart_data = _reshape_for_chart(query_result, chart_config)

    chart_data, adjusted_config = adjust_chart_data(
        chart_data=chart_data,
        chart_config=dict(chart_config),
        profiles=[dict(p) for p in profiles],
    )
    chart_config["x_label"] = adjusted_config.get("x_label")  # type: ignore[literal-required]
    chart_config["y_label"] = adjusted_config.get("y_label")  # type: ignore[literal-required]

    logger.info("[ChartAgent] chart_type=%s", chart_config["chart_type"])

    profiles_as_dicts = [dict(p) for p in profiles]
    return chart_config, chart_data, profiles_as_dicts


async def chart_agent(state: AgentState) -> AgentState:
    """LangGraph node: chạy chart agent trong graph pipeline."""

    forced_chart_type = state.get("forced_chart_type")
    query_result = state.get("query_result", [])
    user_query = state["user_query"]

    chart_config, chart_data, column_profiles = await run_chart_agent(
        user_query=user_query,
        query_result=query_result,
        forced_chart_type=forced_chart_type,
    )

    return {**state, "chart_config": chart_config, "chart_data": chart_data, "column_profiles": column_profiles}