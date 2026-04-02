import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import get_settings
from graph.state import AgentState, TableSchema
from prompts.sql_plan import SQL_PLAN_SYSTEM, SQL_PLAN_HUMAN
from utils.chat_history import format_history

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

def _format_schema_context(schemas: list[TableSchema]) -> str:
    parts = []
    for s in schemas:
        col_lines_arr = []
        for c in s["columns"]:
            c_name = f'"{c["name"]}"'
            c_type = c["type"].upper()
            null_str = " NULL" if c.get("nullable") else " NOT NULL"
            
            extra = []
            if c.get("comment"): extra.append(f"DB Comment: {c['comment']}")
            if c.get("excel_vi_name"): extra.append(f"Tên TV: {c['excel_vi_name']}")
            if c.get("excel_note"): extra.append(f"Ghi chú: {c['excel_note']}")
            
            extra_str = f"  -- {', '.join(extra)}" if extra else ""
            col_lines_arr.append(f"    - {c_name} {c_type}{null_str}{extra_str}")
        
        col_lines = "\n".join(col_lines_arr)
            
        sample = ""
        if s.get("sample_rows"):
            sample = f"\n  Sample: {s['sample_rows'][0]}"
            
        fks_str = ""
        if s.get("foreign_keys"):
            fks = []
            for fk in s["foreign_keys"]:
                fks.append(f"    - {fk['column_name']} REFERENCES {fk['foreign_table']}({fk['foreign_column']})")
            if fks:
                fks_str = "\n  Foreign Keys:\n" + "\n".join(fks)
                
        desc_parts = []
        if s.get("description"): desc_parts.append(f"DB Desc: {s['description']}")
        if s.get("excel_table_desc"): desc_parts.append(f"Tên TV: {s['excel_table_desc']}")
        if s["table_name"] in settings.TABLE_RULES:
            desc_parts.append(f"Quy tắc (BAT BUOC): {settings.TABLE_RULES[s['table_name']]}")
        
        desc = ""
        if desc_parts:
            desc = f"\n  Description: ({' | '.join(desc_parts)})"
            
        parts.append(f'Table: "{s["table_name"]}"{desc}\n{col_lines}{fks_str}{sample}')
    return "\n\n".join(parts)


def _format_business_context(b_ctx: list[dict]) -> str:
    if not b_ctx:
        return "Không có quy định nghiệp vụ nào liên quan."
        
    parts = []
    for c in b_ctx:
        parts.append(f"- Từ khóa: {c['tu_khoa']}\n  Định nghĩa (Logic): {c['dinh_nghia_sql_logic']}")
    return "\n".join(parts)


async def sql_plan_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: generates a reasoning plan for SQL construction.
    Reads: user_query, schema_context, history
    Writes: query_plan
    """
    user_query = state.get("user_query", "")
    schema_context = state.get("schema_context", [])
    history = state.get("history", [])
    history_text = format_history(history)
    
    if not schema_context:
        logger.warning("[SQLPlanAgent] No schemas available. Skipping plan.")
        return {**state, "query_plan": "No schema information provided."}

    schema_str = _format_schema_context(schema_context)
    business_ctx = state.get("business_context", [])
    business_str = _format_business_context(business_ctx)

    messages = [
        SystemMessage(content=SQL_PLAN_SYSTEM),
        HumanMessage(content=SQL_PLAN_HUMAN.format(
            user_query=user_query,
            schema_context=schema_str,
            business_context=business_str,
            history_text=history_text
        )),
    ]

    logger.info("[SQLPlanAgent] Generating reasoning plan for query=%r, history_len=%d...", user_query, len(history))
    response = await _llm.ainvoke(messages)
    query_plan = ""
    query_plan = response.content.strip()

    logger.info("[SQLPlanAgent] Generated Plan:\n%s", query_plan)

    return {**state, "query_plan": query_plan}
