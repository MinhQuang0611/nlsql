from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage
from sqlalchemy import text
from qdrant_client import QdrantClient

from config import get_settings
from db.connection import get_db_context, ch_execute
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
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


@lru_cache(maxsize=1)
def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


# ---------------------------------------------------------------------------
# SQL queries — Postgres
# ---------------------------------------------------------------------------

_PG_GET_TABLES = text("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
""")

_PG_GET_TABLE_DESC = text("""
    SELECT obj_description(pg_class.oid, 'pg_class') AS description
    FROM pg_class
    JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
    WHERE pg_namespace.nspname = 'public' AND pg_class.relname = :table_name
""")

_PG_GET_FOREIGN_KEYS = text("""
    SELECT
        kcu.column_name,
        ccu.table_name AS foreign_table,
        ccu.column_name AS foreign_column
    FROM information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
      ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
      ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name = :table_name
""")

_PG_GET_COLUMNS = text("""
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


# ---------------------------------------------------------------------------
# SQL queries — ClickHouse
# ---------------------------------------------------------------------------

_CH_GET_TABLES = "SHOW TABLES"

_CH_GET_COLUMNS = """
    SELECT
        name        AS column_name,
        type        AS data_type,
        comment     AS comment
    FROM system.columns
    WHERE database = '{db}' AND table = '{table}'
    ORDER BY position
"""

_CH_GET_SAMPLE = "SELECT * FROM `{table}` LIMIT 3"
_PG_GET_SAMPLE = 'SELECT * FROM "{table}" LIMIT 3'


# ---------------------------------------------------------------------------
# Fetch helpers — Postgres
# ---------------------------------------------------------------------------

async def _pg_fetch_all_tables(domain: str) -> list[str]:
    async with get_db_context(domain) as db:
        result = await db.execute(_PG_GET_TABLES)
        return [row[0] for row in result.fetchall()]


async def _pg_fetch_table_schema(domain: str, table_name: str) -> TableSchema:
    async with get_db_context(domain) as db:
        desc_row = (await db.execute(_PG_GET_TABLE_DESC, {"table_name": table_name})).fetchone()
        description = desc_row[0] if desc_row and desc_row[0] else None

        fk_rows = (await db.execute(_PG_GET_FOREIGN_KEYS, {"table_name": table_name})).fetchall()
        foreign_keys = [
            {"column_name": r.column_name, "foreign_table": r.foreign_table, "foreign_column": r.foreign_column}
            for r in fk_rows
        ]

        col_rows = (await db.execute(_PG_GET_COLUMNS, {"table_name": table_name})).fetchall()
        columns: list[TableColumn] = [
            TableColumn(
                name=r.column_name,
                type=r.data_type,
                nullable=r.is_nullable == "YES",
                comment=r.comment,
            )
            for r in col_rows
        ]

        sample_rows_raw = (await db.execute(text(_PG_GET_SAMPLE.format(table=table_name)))).fetchall()
        sample_rows = [dict(r._mapping) for r in sample_rows_raw]

    return TableSchema(
        table_name=table_name,
        description=description,
        columns=columns,
        foreign_keys=foreign_keys,
        sample_rows=sample_rows,
    )


# ---------------------------------------------------------------------------
# Fetch helpers — ClickHouse
# ---------------------------------------------------------------------------

async def _ch_fetch_all_tables(domain: str) -> list[str]:
    rows = await ch_execute(domain, _CH_GET_TABLES)
    return [row[0] for row in rows]


async def _ch_fetch_table_schema(domain: str, table_name: str) -> TableSchema:
    col_sql = _CH_GET_COLUMNS.format(db=settings.get_db_name(domain), table=table_name)
    col_rows = await ch_execute(domain, col_sql)

    columns: list[TableColumn] = [
        TableColumn(
            name=row[0],
            type=row[1],
            nullable=False,   # ClickHouse dùng Nullable(T) trong type string
            comment=row[2] if len(row) > 2 else None,
        )
        for row in col_rows
    ]

    sample_sql = _CH_GET_SAMPLE.format(table=table_name)
    sample_raw = await ch_execute(domain, sample_sql)
    if sample_raw and hasattr(sample_raw[0], "_mapping"):
        sample_rows = [dict(r._mapping) for r in sample_raw]
    elif sample_raw and hasattr(sample_raw[0], "_fields"):
        sample_rows = [r._asdict() for r in sample_raw]
    else:
        col_names = [c["name"] for c in columns]
        sample_rows = [dict(zip(col_names, row)) for row in sample_raw]

    return TableSchema(
        table_name=table_name,
        description=None,       # ClickHouse không có table-level description
        columns=columns,
        foreign_keys=[],        # ClickHouse không có FK
        sample_rows=sample_rows,
    )


# ---------------------------------------------------------------------------
# Unified helpers (route theo active_db)
# ---------------------------------------------------------------------------

async def _fetch_all_tables(domain: str) -> list[str]:
    if settings.active_db == "clickhouse":
        return await _ch_fetch_all_tables(domain)
    return await _pg_fetch_all_tables(domain)


async def _fetch_table_schema(domain: str, table_name: str) -> TableSchema:
    if settings.active_db == "clickhouse":
        return await _ch_fetch_table_schema(domain, table_name)
    return await _pg_fetch_table_schema(domain, table_name)


# ---------------------------------------------------------------------------
# schema_agent node
# ---------------------------------------------------------------------------

async def schema_agent(state: AgentState) -> AgentState:
    domain = state.get("domain", "qldt")
    user_query = state["user_query"]
    selected_tables = state.get("selected_tables")

    if selected_tables:
        logger.info("[SchemaAgent] Giới hạn truy vấn trong các bảng được chọn: %s", selected_tables)
        try:
            schema_context = [await _fetch_table_schema(domain, t) for t in selected_tables]
            return {"relevant_tables": selected_tables, "schema_context": schema_context}
        except Exception as exc:
            logger.error("[SchemaAgent] Lỗi khi lấy schema cho selected_tables: %s", exc)
            return {"relevant_tables": [], "schema_context": []}

    SCORE_THRESHOLD = 0.68
    SEARCH_LIMIT = 20

    logger.info("[SchemaAgent] Qdrant semantic search for: %r", user_query)
    relevant_tables: list[str] = []
    schema_context: list = []

    try:
        qdrant = _get_qdrant_client()
        embeddings = _get_embeddings()

        vector = embeddings.embed_query(user_query)
        response = qdrant.query_points(
            collection_name=f"schema_collection_{domain}",
            query=vector,
            limit=SEARCH_LIMIT,
            with_payload=True,
        )
        search_result = response.points

        # Dedup: keep highest-score hit per table_name
        best: dict[str, Any] = {}
        for hit in search_result:
            if not hit.payload:
                continue
            tname = hit.payload.get("table_name", "")
            score = hit.score if hasattr(hit, "score") else 0.0
            if tname not in best or score > best[tname].score:
                best[tname] = hit

        passed = [(t, h) for t, h in best.items() if h.score >= SCORE_THRESHOLD]
        passed.sort(key=lambda x: x[1].score, reverse=True)

        if passed:
            score_log = ", ".join(f"{t}={h.score:.3f}" for t, h in passed)
            logger.info("[SchemaAgent] Tables passed threshold (%.2f): %s", SCORE_THRESHOLD, score_log)
        else:
            all_scores = ", ".join(
                f"{t}={h.score:.3f}"
                for t, h in sorted(best.items(), key=lambda x: x[1].score, reverse=True)
            )
            logger.warning("[SchemaAgent] No table >= %.2f. All scores: %s", SCORE_THRESHOLD, all_scores)

        for tname, hit in passed:
            relevant_tables.append(tname)
            schema_context.append(json.loads(hit.payload["schema_json"]))

        # LLM fallback khi tìm được < 2 bảng
        if len(relevant_tables) < 2:
            logger.warning(
                "[SchemaAgent] Only %d table(s) found via vector search. Falling back to LLM.",
                len(relevant_tables),
            )
            try:
                all_table_names = await _fetch_all_tables(domain)
                table_list_str = "\n".join(f"- {t}" for t in all_table_names)
                rules_str = "\n".join(f"- {k}: {v}" for k, v in settings.TABLE_RULES.items())
                fallback_prompt = (
                    f"Người dùng hỏi: {user_query}\n\n"
                    f"Danh sách tất cả các bảng trong cơ sở dữ liệu:\n{table_list_str}\n\n"
                    f"Lưu ý các quy tắc chọn bảng (RẤT QUAN TRỌNG):\n{rules_str}\n\n"
                    "Hãy liệt kê tên các bảng CÓ THỂ LIÊN QUAN đến câu hỏi trên. Cố gắng chọn tối đa 5 bảng chính xác nhất.\n"
                    "Chỉ trả lời bằng danh sách tên bảng, mỗi bảng trên một dòng, không giải thích."
                )
                llm_response = _llm.invoke([HumanMessage(content=fallback_prompt)])
                llm_tables = [
                    line.strip().lstrip("- ").strip()
                    for line in llm_response.content.strip().splitlines()
                    if line.strip()
                ]
                existing = set(relevant_tables)
                valid_all = set(all_table_names)
                new_tables = [t for t in llm_tables if t in valid_all and t not in existing]
                logger.info("[SchemaAgent] LLM fallback suggested: %s → valid new: %s", llm_tables, new_tables)

                for tname in new_tables:
                    schema = await _fetch_table_schema(domain, tname)
                    relevant_tables.append(tname)
                    schema_context.append(schema)

            except Exception as fallback_exc:
                logger.error("[SchemaAgent] LLM fallback failed: %s", fallback_exc)

    except Exception as exc:
        logger.error("[SchemaAgent] Qdrant search failed: %s. Ensure Qdrant is running and populated.", exc)

    logger.info("[SchemaAgent] Final relevant_tables = %s", relevant_tables)
    return {"relevant_tables": relevant_tables, "schema_context": schema_context}