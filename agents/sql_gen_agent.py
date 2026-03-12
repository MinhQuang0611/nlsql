
from __future__ import annotations

import json
import logging
import asyncio
from collections import Counter

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import QdrantClient

from config import get_settings
from graph.state import AgentState, TableSchema
from prompts.sql_gen import SQL_GEN_SYSTEM, SQL_GEN_HUMAN, SQL_GEN_RETRY_HINT

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)

_llm_creative = ChatOpenAI(
    model=settings.openai_model,
    temperature=0.7,
    api_key=settings.openai_api_key,
)

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
        desc = ""
        if desc_parts:
            desc = f"\n  Description: ({' | '.join(desc_parts)})"
            
        parts.append(f'Table: "{s["table_name"]}"{desc}\n{col_lines}{fks_str}{sample}')
    return "\n\n".join(parts)


async def sql_gen_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: generate SQL from natural language.

    Reads  : state["user_query"], state["schema_context"],
             state["retry_count"], state["sql_check"] (on retry)
    Writes : state["generated_sql"], state["sql_reasoning"]
    """
    user_query = state["user_query"]
    schema_context = state.get("schema_context", [])
    retry_count = state.get("retry_count", 0)
    schema_str = _format_schema_context(schema_context)

    retry_hint = ""
    if retry_count > 0:
        prev_check = state.get("sql_check", {})
        issues = prev_check.get("issues", [])
        prev_sql = state.get("generated_sql", "")
        retry_hint = SQL_GEN_RETRY_HINT.format(
            issues="\n".join(f"  - {i}" for i in issues),
            previous_sql=prev_sql,
        )

    logger.info("[SQLGenAgent] attempt=%d query=%r", retry_count + 1, user_query)

    # 1. Fetch Few-Shot Examples from Qdrant
    few_shot_str = "Không tìm thấy ví dụ (No few shot available)."
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
        logger.warning(f"[SQLGenAgent] Qdrant few-shot retrieval failed: {exc}")

    messages = [
        SystemMessage(content=SQL_GEN_SYSTEM),
        HumanMessage(content=SQL_GEN_HUMAN.format(
            user_query=user_query,
            schema_context=schema_str,
            few_shot_examples=few_shot_str,
            retry_hint=retry_hint,
        )),
    ]

    # 2. Self-Consistency Voting (generate 3 outputs)
    NUM_SAMPLES = 3
    # Use creative LLM with higher temperature to ge variations
    logger.info("[SQLGenAgent] Initiating self-consistency parallel generation...")
    tasks = [_llm_creative.ainvoke(messages) for _ in range(NUM_SAMPLES)]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    candidates = []
    
    for resp in responses:
        if isinstance(resp, Exception):
            logger.error(f"[SQLGenAgent] Candidate generation failed: {resp}")
            continue
            
        raw = resp.content.strip()
        try:
            parsed = json.loads(raw)
            sql = parsed.get("sql", "").strip()
            reasoning = parsed.get("reasoning", "")
            if sql:
                candidates.append({"sql": sql, "reasoning": reasoning})
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error("[SQLGenAgent] Candidate parse error: %s | raw=%r", exc, raw)

    if not candidates:
        generated_sql = "SELECT 1; -- Fallback: all generation tasks failed"
        sql_reasoning = "All generations failed to parse JSON."
    else:
        # Find the most frequent SQL (ignoring minor whitespace differences)
        normalized_sqls = [c["sql"].replace('\n', ' ').strip().lower() for c in candidates]
        counter = Counter(normalized_sqls)
        best_normalized_sql, count = counter.most_common(1)[0]
        
        logger.info(f"[SQLGenAgent] Self-consistency picked SQL with {count}/{len(candidates)} votes.")
        
        # Recover the original formatting of the chosen normalized SQL
        best_candidate = next(c for c in candidates if c["sql"].replace('\n', ' ').strip().lower() == best_normalized_sql)
        
        generated_sql = best_candidate["sql"]
        sql_reasoning = best_candidate["reasoning"]

    logger.info("[SQLGenAgent] generated_sql=\n%s", generated_sql)
    return {**state, "generated_sql": generated_sql, "sql_reasoning": sql_reasoning}