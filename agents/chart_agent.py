"""
Chọn kiểu biểu đồ và map trục từ kết quả SQL.

Trước đây mọi câu data_query đều tốn một lượt LLM ở đây, dù người dùng không xin
biểu đồ. Nhưng toàn bộ "quy tắc chọn chart" trong prompt cũ đều quyết định được
từ column_profiles (kiểu cột, vai trò dimension/measure, số giá trị phân biệt).
Nay chọn bằng luật; LLM chỉ được gọi khi người dùng XIN biểu đồ và dữ liệu có
nhiều cách map trục hợp lệ (nhiều dimension hoặc nhiều measure).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from graph.state import AgentState, ChartConfig
from prompts.chart import CHART_SYSTEM, CHART_HUMAN, CHART_HUMAN_FORCED
from utils.chart_adjustment import adjust_chart_data
from utils.data_profiler import ColumnProfile, profile_columns, format_profile_for_prompt
from utils.llm import make_llm

logger = logging.getLogger(__name__)

_llm = make_llm()

VALID_CHART_TYPES = {"bar", "line", "pie", "table", "number", "scatter"}

# Từ khoá trong câu hỏi gợi ý người dùng muốn xem tỉ lệ / cơ cấu → pie thay vì bar.
_PIE_HINT = re.compile(r"(tỉ lệ|tỷ lệ|phần trăm|cơ cấu|biểu đồ tròn|pie)", re.IGNORECASE)
_MAX_PIE_GROUPS = 8
_MAX_LINE_GROUPS = 10


def _table_config(title: str) -> ChartConfig:
    return ChartConfig(chart_type="table", x_axis=None, y_axis=None, group_by=None,
                       title=title, x_label=None, y_label=None)


def _rule_based_config(
    rows: list[dict[str, Any]],
    profiles: list[ColumnProfile],
    user_query: str,
    forced_chart_type: Optional[str],
) -> ChartConfig:
    """Áp dụng đúng thứ tự ưu tiên của prompt cũ, nhưng bằng code."""
    title = user_query[:60]
    dates = [p for p in profiles if p["inferred_type"] == "date"]
    measures = [p for p in profiles if p["role"] == "measure"]
    dims = [p for p in profiles if p["role"] == "dimension" and p["inferred_type"] != "date"]

    def cfg(chart_type: str, x=None, y=None, group=None) -> ChartConfig:
        return ChartConfig(chart_type=chart_type, x_axis=x, y_axis=y, group_by=group,
                           title=title, x_label=x, y_label=y)

    # Người dùng ép kiểu: map trục tốt nhất có thể cho kiểu đó.
    if forced_chart_type:
        if forced_chart_type == "table":
            return _table_config(title)
        if forced_chart_type == "number":
            return cfg("number")
        if forced_chart_type == "scatter" and len(measures) >= 2:
            return cfg("scatter", measures[0]["col_name"], measures[1]["col_name"],
                       dims[0]["col_name"] if dims else None)
        x = (dates or dims or measures)[0]["col_name"] if profiles else None
        y_candidates = [m for m in measures if m["col_name"] != x]
        y = y_candidates[0]["col_name"] if y_candidates else None
        group = None
        if forced_chart_type in ("bar", "line"):
            others = [d for d in dims if d["col_name"] != x and d["n_unique"] <= _MAX_LINE_GROUPS]
            group = others[0]["col_name"] if others else None
        return cfg(forced_chart_type, x, y, group)

    # 1. Một ô số duy nhất → KPI
    if len(rows) == 1 and len(profiles) == 1 and measures:
        return cfg("number")
    # Một dòng nhiều cột → bảng, không có gì để vẽ
    if len(rows) == 1:
        return _table_config(title)
    if not measures:
        return _table_config(title)

    y = measures[0]["col_name"]

    # 2. Có cột thời gian + cột số → đường
    if dates:
        x = dates[0]["col_name"]
        group = next((d["col_name"] for d in dims if d["n_unique"] <= _MAX_LINE_GROUPS), None)
        return cfg("line", x, y, group)

    # 3 & 4. Một dimension + số → pie (nếu hỏi tỉ lệ và ít nhóm) hoặc bar
    if dims:
        x = dims[0]["col_name"]
        n_groups = dims[0]["n_unique"]
        if _PIE_HINT.search(user_query) and n_groups <= _MAX_PIE_GROUPS and len(measures) == 1:
            return cfg("pie", x, y)
        group = next((d["col_name"] for d in dims[1:] if d["n_unique"] <= _MAX_LINE_GROUPS), None)
        return cfg("bar", x, y, group)

    # 5. Không dimension, ≥2 measure → scatter
    if len(measures) >= 2 and len(rows) >= 3:
        return cfg("scatter", measures[0]["col_name"], measures[1]["col_name"])

    return _table_config(title)


def _is_ambiguous(profiles: list[ColumnProfile]) -> bool:
    """Nhiều hơn một cách map trục hợp lệ — lúc này mới đáng hỏi LLM."""
    measures = sum(1 for p in profiles if p["role"] == "measure")
    dims = sum(1 for p in profiles if p["role"] == "dimension")
    return measures > 1 or dims > 1


def _parse_llm_response(raw: str, fallback: ChartConfig, columns: list[str]) -> ChartConfig:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("[ChartAgent] LLM trả JSON hỏng: %s", exc)
        return fallback

    chart_type = parsed.get("chart_type", fallback["chart_type"])
    if chart_type not in VALID_CHART_TYPES:
        chart_type = fallback["chart_type"]

    def col(key: str):
        v = parsed.get(key)
        return v if v in columns else None

    return ChartConfig(
        chart_type=chart_type,
        x_axis=col("x_axis"), y_axis=col("y_axis"), group_by=col("group_by"),
        title=parsed.get("title") or fallback["title"],
        x_label=parsed.get("x_label"), y_label=parsed.get("y_label"),
    )


async def _llm_config(
    user_query: str,
    rows: list[dict[str, Any]],
    profiles: list[ColumnProfile],
    forced_chart_type: Optional[str],
    fallback: ChartConfig,
) -> ChartConfig:
    columns = list(rows[0].keys())
    kwargs = dict(
        user_query=user_query, columns=columns,
        column_profile=format_profile_for_prompt(profiles), sample_rows=rows[:3],
    )
    human = (CHART_HUMAN_FORCED.format(forced_chart_type=forced_chart_type, **kwargs)
             if forced_chart_type else CHART_HUMAN.format(**kwargs))
    try:
        response = await _llm.ainvoke([SystemMessage(content=CHART_SYSTEM), HumanMessage(content=human)])
        config = _parse_llm_response(response.content.strip(), fallback, columns)
    except Exception as exc:
        logger.error("[ChartAgent] LLM lỗi, dùng cấu hình theo luật: %s", exc)
        return fallback
    if forced_chart_type and config["chart_type"] != forced_chart_type:
        config["chart_type"] = forced_chart_type  # type: ignore[typeddict-item]
    return config


def _reshape_for_chart(rows: list[dict[str, Any]], config: ChartConfig) -> list[dict[str, Any]]:
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


async def run_chart_agent(
    user_query: str,
    query_result: list[dict[str, Any]],
    forced_chart_type: Optional[str] = None,
    allow_llm: bool = False,
) -> tuple[ChartConfig, list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Args:
        user_query: câu hỏi của người dùng
        query_result: dữ liệu thô từ database
        forced_chart_type: nếu có, ép dùng loại chart này
        allow_llm: cho phép hỏi LLM khi dữ liệu có nhiều cách map trục
                   (chỉ bật khi người dùng thực sự xin biểu đồ)

    Returns:
        (chart_config, chart_data, column_profiles)
    """
    if not query_result:
        return _table_config(user_query[:60]), [], []

    if forced_chart_type and forced_chart_type not in VALID_CHART_TYPES:
        logger.warning("[ChartAgent] forced_chart_type=%s không hợp lệ, bỏ qua", forced_chart_type)
        forced_chart_type = None

    profiles = profile_columns(query_result)
    chart_config = _rule_based_config(query_result, profiles, user_query, forced_chart_type)

    if allow_llm and _is_ambiguous(profiles):
        logger.info("[ChartAgent] dữ liệu có nhiều cách map trục — hỏi LLM")
        chart_config = await _llm_config(user_query, query_result, profiles, forced_chart_type, chart_config)

    chart_data = _reshape_for_chart(query_result, chart_config)
    chart_data, adjusted = adjust_chart_data(
        chart_data=chart_data, chart_config=dict(chart_config), profiles=[dict(p) for p in profiles],
    )
    chart_config["x_label"] = adjusted.get("x_label")  # type: ignore[typeddict-item]
    chart_config["y_label"] = adjusted.get("y_label")  # type: ignore[typeddict-item]

    logger.info("[ChartAgent] chart_type=%s x=%s y=%s group=%s", chart_config["chart_type"],
                chart_config.get("x_axis"), chart_config.get("y_axis"), chart_config.get("group_by"))
    return chart_config, chart_data, [dict(p) for p in profiles]


async def chart_agent(state: AgentState) -> dict:
    """LangGraph node. Chỉ hỏi LLM khi intent là chart_request hoặc API ép chart."""
    wants_chart = state.get("intent") == "chart_request" or bool(state.get("force_chart"))
    chart_config, chart_data, column_profiles = await run_chart_agent(
        user_query=state["user_query"],
        query_result=state.get("query_result", []),
        forced_chart_type=state.get("forced_chart_type"),
        allow_llm=wants_chart,
    )
    return {"chart_config": chart_config, "chart_data": chart_data, "column_profiles": column_profiles}
