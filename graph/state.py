from __future__ import annotations

from typing import Any, Literal, Optional
from typing_extensions import TypedDict


class TableColumn(TypedDict, total=False):
    name: str
    type: str
    nullable: bool
    comment: Optional[str]
    excel_vi_name: Optional[str]
    excel_note: Optional[str]


class TableSchema(TypedDict, total=False):
    table_name: str
    description: Optional[str]
    excel_table_desc: Optional[str]
    columns: list[TableColumn]
    foreign_keys: Optional[list[dict]]
    sample_rows: Optional[list[dict]]


class ChartConfig(TypedDict):
    chart_type: Literal["bar", "line", "pie", "table", "number", "scatter"]
    x_axis: Optional[str]
    y_axis: Optional[str]
    group_by: Optional[str]
    title: str
    x_label: Optional[str]
    y_label: Optional[str]


class SQLCorrectionResult(TypedDict):
    is_valid: bool
    issues: list[str]
    fixed_sql: Optional[str]


Intent = Literal[
    "data_query",
    "chart_request",
    "schema_question",
    "knowledge_query",
    "domain_query",
    "greeting",
    "out_of_scope",
    "ambiguous",
    "faq_answered",
]


class AgentState(TypedDict, total=False):
    # ── Input ────────────────────────────────────────────────────────────
    user_query: str
    session_id: str
    history: list[dict]                      # [{"role": "user"/"assistant", "content": ...}]
    selected_tables: Optional[list[str]]     # /chat_with_table: giới hạn bảng
    forced_chart_type: Optional[str]         # ép kiểu biểu đồ
    force_chart: bool                        # cho phép chart_agent hỏi LLM dù intent không phải chart_request

    # ── router ───────────────────────────────────────────────────────────
    # Domain = một nguồn dữ liệu trong registry (config.Settings.list_domains()).
    # Được set sẵn bởi endpoint /<domain>/chat, hoặc do router_agent chọn.
    domain: str
    domain_reasoning: Optional[str]
    intent: Intent
    clarification_question: Optional[str]

    # ── retrieval ────────────────────────────────────────────────────────
    relevant_tables: list[str]
    schema_context: list[TableSchema]
    knowledge_context: Optional[str]
    business_context: list[dict]

    # ── sql ──────────────────────────────────────────────────────────────
    generated_sql: str
    sql_reasoning: str                       # kế hoạch suy luận (plan) của sql_gen
    sql_correction: SQLCorrectionResult
    final_sql: str
    retry_count: int                         # số lần sql_check từ chối

    # ── execute / data_check ─────────────────────────────────────────────
    query_result: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float
    executor_error: Optional[str]
    data_check_is_valid: bool
    data_check_issues: list[str]
    data_retry_count: int                    # số lần data_check từ chối

    # ── chart / answer ───────────────────────────────────────────────────
    column_profiles: Optional[list[dict]]
    chart_config: Optional[ChartConfig]
    chart_data: Optional[list[dict]]
    recommend_questions: Optional[list[str]]
    answer: str
    answer_format: Literal["text", "table", "chart+text"]
