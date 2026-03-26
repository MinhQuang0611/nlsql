
from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text
from qdrant_client import QdrantClient

from config import get_settings
from db.connection import get_db_context
from graph.state import AgentState, TableColumn, TableSchema
from prompts.schema_prune import SCHEMA_SYSTEM, SCHEMA_HUMAN

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = ChatOpenAI(
    model=settings.openai_model,
    temperature=0,
    api_key=settings.openai_api_key,
)


@lru_cache(maxsize=1)
def _get_qdrant_client() -> QdrantClient:
    """Singleton QdrantClient — created once, reused across all requests."""
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    """Singleton OpenAIEmbeddings — created once, reused across all requests."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )



_GET_TABLES_SQL = text("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")

_GET_TABLE_DESC_SQL = text("""
    SELECT obj_description(pg_class.oid, 'pg_class') AS description
    FROM pg_class
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    WHERE pg_namespace.nspname = 'public' AND pg_class.relname = :table_name
""")

_GET_FOREIGN_KEYS_SQL = text("""
    SELECT
        kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name
      AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name
      AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = :table_name
""")

_GET_COLUMNS_SQL = text("""
    SELECT
        c.column_name,
        c.data_type,
        c.is_nullable,
        pgd.description as comment
    FROM information_schema.columns c
    JOIN pg_class t ON c.table_name = t.relname
    JOIN pg_namespace ns ON ns.oid = t.relnamespace AND ns.nspname = c.table_schema
    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attname = c.column_name AND a.attnum > 0
    LEFT JOIN pg_description pgd ON pgd.objoid = t.oid AND pgd.objsubid = a.attnum
    WHERE c.table_schema = 'public'
      AND c.table_name = :table_name
    ORDER BY c.ordinal_position
""")

_GET_SAMPLE_SQL = 'SELECT * FROM "{table}" LIMIT 3'


async def _fetch_all_tables() -> list[str]:
    async with get_db_context() as db:
        result = await db.execute(_GET_TABLES_SQL)
        return [row[0] for row in result.fetchall()]


async def _fetch_table_schema(table_name: str) -> TableSchema:
    async with get_db_context() as db:
        desc_result = await db.execute(_GET_TABLE_DESC_SQL, {"table_name": table_name})
        desc_row = desc_result.fetchone()
        description = desc_row[0] if desc_row and desc_row[0] else None

        fk_result = await db.execute(_GET_FOREIGN_KEYS_SQL, {"table_name": table_name})
        foreign_keys = [
            {
                "column_name": row.column_name,
                "foreign_table": row.foreign_table,
                "foreign_column": row.foreign_column,
            }
            for row in fk_result.fetchall()
        ]

        col_result = await db.execute(_GET_COLUMNS_SQL, {"table_name": table_name})
        columns: list[TableColumn] = [
            TableColumn(
                name=row.column_name,
                type=row.data_type,
                nullable=row.is_nullable == "YES",
                comment=row.comment,
            )
            for row in col_result.fetchall()
        ]

        sample_result = await db.execute(
            text(_GET_SAMPLE_SQL.format(table=table_name))
        )
        sample_rows: list[dict[str, Any]] = [
            dict(row._mapping) for row in sample_result.fetchall()
        ]

    return TableSchema(
        table_name=table_name,
        description=description,
        columns=columns,
        foreign_keys=foreign_keys,
        sample_rows=sample_rows,
    )


def _format_table_list(schemas: list[TableSchema]) -> str:
    lines = []
    for s in schemas:
        cols = ", ".join(f"{c['name']} ({c['type']})" for c in s["columns"])
        lines.append(f"- {s['table_name']}: {cols}")
    return "\n".join(lines)



async def schema_agent(state: AgentState) -> AgentState:
    """
    LangGraph node: select relevant tables and build schema context.
    Uses Qdrant semantic search with score threshold, dedup, and LLM fallback.

    Reads  : state["user_query"]
    Writes : state["relevant_tables"], state["schema_context"]
    """
    user_query = state["user_query"]
    selected_tables = state.get("selected_tables")

    if selected_tables:
        logger.info(f"[SchemaAgent] Giới hạn truy vấn trong các bảng được chọn: {selected_tables}")
        try:
            schema_context = []
            for table in selected_tables:
                schema = await _fetch_table_schema(table)
                schema_context.append(schema)
            return {**state, "relevant_tables": selected_tables, "schema_context": schema_context}
        except Exception as exc:
            logger.error(f"[SchemaAgent] Lỗi khi lấy schema cho selected_tables: {exc}")
            return {**state, "relevant_tables": [], "schema_context": []}

    SCORE_THRESHOLD = 0.68
    SEARCH_LIMIT = 20

    logger.info(f"[SchemaAgent] Qdrant semantic search for: {user_query!r}")

    relevant_tables: list[str] = []
    schema_context: list = []

    try:
        qdrant = _get_qdrant_client()
        embeddings = _get_embeddings()

        vector = embeddings.embed_query(user_query)
        response = qdrant.query_points(
            collection_name="schema_collection",
            query=vector,
            limit=SEARCH_LIMIT,
            with_payload=True,
        )
        search_result = response.points

        # --- Dedup: keep highest-score hit per table_name ---
        best: dict[str, Any] = {}  # table_name -> hit
        for hit in search_result:
            if not hit.payload:
                continue
            tname = hit.payload.get("table_name", "")
            score = hit.score if hasattr(hit, "score") else 0.0
            if tname not in best or score > best[tname].score:
                best[tname] = hit

        # --- Score threshold filter + logging ---
        passed = [(tname, hit) for tname, hit in best.items() if hit.score >= SCORE_THRESHOLD]
        passed.sort(key=lambda x: x[1].score, reverse=True)

        if passed:
            score_log = ", ".join(f"{t}={h.score:.3f}" for t, h in passed)
            logger.info(f"[SchemaAgent] Tables passed threshold ({SCORE_THRESHOLD}): {score_log}")
        else:
            all_scores = ", ".join(f"{t}={h.score:.3f}" for t, h in sorted(best.items(), key=lambda x: x[1].score, reverse=True))
            logger.warning(f"[SchemaAgent] No table >= {SCORE_THRESHOLD}. All scores: {all_scores}")

        for tname, hit in passed:
            relevant_tables.append(tname)
            schema_context.append(json.loads(hit.payload["schema_json"]))

        # --- LLM fallback when fewer than 2 tables found ---
        if len(relevant_tables) < 2:
            logger.warning(
                f"[SchemaAgent] Only {len(relevant_tables)} table(s) found via vector search. "
                "Falling back to LLM for table selection."
            )
            try:
                all_table_names = await _fetch_all_tables()
                table_list_str = "\n".join(f"- {t}" for t in all_table_names)
                fallback_prompt = (
                    f"Người dùng hỏi: {user_query}\n\n"
                    f"Danh sách tất cả các bảng trong cơ sở dữ liệu:\n{table_list_str}\n\n"
                    "Hãy liệt kê tên các bảng CÓ THỂ LIÊN QUAN đến câu hỏi trên. "
                    "Chỉ trả lời bằng danh sách tên bảng, mỗi bảng trên một dòng, không giải thích."
                )
                llm_response = _llm.invoke([HumanMessage(content=fallback_prompt)])
                llm_tables = [
                    line.strip().lstrip("- ").strip()
                    for line in llm_response.content.strip().splitlines()
                    if line.strip()
                ]
                # Only add tables that actually exist and aren't already included
                existing = set(relevant_tables)
                valid_all = set(all_table_names)
                new_tables = [t for t in llm_tables if t in valid_all and t not in existing]
                logger.info(f"[SchemaAgent] LLM fallback suggested: {llm_tables} → valid new: {new_tables}")

                for tname in new_tables:
                    schema = await _fetch_table_schema(tname)
                    relevant_tables.append(tname)
                    schema_context.append(schema)
            except Exception as fallback_exc:
                logger.error(f"[SchemaAgent] LLM fallback failed: {fallback_exc}")

    except Exception as exc:
        logger.error(f"[SchemaAgent] Qdrant search failed: {exc}. Ensure Qdrant is running and populated.")
        relevant_tables = []
        schema_context = []

    logger.info(f"[SchemaAgent] Final relevant_tables = {relevant_tables}")
    return {**state, "relevant_tables": relevant_tables, "schema_context": schema_context}