from __future__ import annotations

import logging
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient

from config import get_settings
from graph.state import AgentState, TableSchema
from prompts.sql_gen import SQL_GEN_SYSTEM, SQL_GEN_HUMAN, SQL_GEN_RETRY_HINT
from utils.chat_history import format_history

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.sql_gen_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

class SQLGenerationSchema(BaseModel):
    sql: str = Field(description="Câu lệnh PostgreSQL query thuần túy")
    reasoning: str = Field(description="Giải thích ngắn gọn lý do sinh ra câu lệnh SQL này")


def _format_schema_context(schemas: list[TableSchema]) -> str:
    """Render schema_context list into a readable string for the prompt."""
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


async def sql_gen_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: generate SQL from natural language using the reasoning plan.
    Reads  : user_query, schema_context, query_plan
    Writes : generated_sql, sql_reasoning, (clears sql_correction logic)
    """
    user_query = state.get("user_query", "")
    schema_context = state.get("schema_context", [])
    query_plan = state.get("query_plan", "")
    retry_count = state.get("retry_count", 0)
    history = state.get("history", [])
    
    schema_str = _format_schema_context(schema_context)

    history_text = format_history(history)

    retry_hint = ""
    if retry_count > 0:
        prev_check = state.get("sql_correction", {})
        issues = prev_check.get("issues", [])
        retry_hint = SQL_GEN_RETRY_HINT.format(
            issues="\n".join(f"  - {i}" for i in issues)
        )

    logger.info("[SQLGenAgent] attempt=%d query=%r, history_len=%d", retry_count + 1, user_query, len(history))

    # 1. Fetch Few-Shot Examples from Qdrant
    few_shot_str = "Không tìm thấy ví dụ (No few shot available)."
    if settings.qdrant_url and settings.qdrant_api_key:
        try:
            qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
            embeddings = OpenAIEmbeddings(
                model=settings.embedding_model, 
                api_key=settings.openai_api_key
            )
            
            vector = embeddings.embed_query(user_query)
            response = qdrant.query_points(
                collection_name="few_shot_collection",
                query=vector,
                limit=3
            )
            search_result = response.points
            if search_result:
                lines = []
                for hit in search_result:
                    if hit.payload:
                        lines.append(f"Q: {hit.payload['question']}\nSQL: {hit.payload['sql']}")
                if lines:
                    few_shot_str = "\n\n".join(lines)
                logger.info(f"[SQLGenAgent] Retrieved {len(lines)} few-shot examples.")
        except Exception as exc:
            logger.warning(f"[SQLGenAgent] Qdrant few-shot retrieval failed or skipped: {exc}")

    messages = [
        SystemMessage(content=SQL_GEN_SYSTEM),
        HumanMessage(content=SQL_GEN_HUMAN.format(
            user_query=user_query,
            query_plan=query_plan,
            schema_context=schema_str,
            few_shot_examples=few_shot_str,
            retry_hint=retry_hint,
            history_text=history_text,
        )),
    ]

    llm_structured = _llm.with_structured_output(SQLGenerationSchema)
    
    generated_sql = ""
    sql_reasoning = ""

    try:
        response = await llm_structured.ainvoke(messages)
        generated_sql = response.sql.strip()
        sql_reasoning = response.reasoning
    except Exception as exc:
        logger.error("[SQLGenAgent] SQL generation failed: %s", exc, exc_info=True)

    logger.info("[SQLGenAgent] generated_sql=\n%s", generated_sql)
    
    # Return fresh state for correction logic down the line
    return {
        **state, 
        "generated_sql": generated_sql, 
        "sql_reasoning": sql_reasoning,
        # Clear out any past corrections as this is a fresh generation
        "sql_correction": {"is_valid": False, "issues": [], "fixed_sql": None},
        "final_sql": ""
    }