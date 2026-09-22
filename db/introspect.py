"""
Introspect cấu trúc bảng của một domain (PostgreSQL hoặc ClickHouse).

Tách khỏi schema_agent để agent chỉ còn logic retrieval; scripts/index_schema.py
và đường selected_tables dùng chung các hàm này.
"""
from __future__ import annotations

from sqlalchemy import text

from config import get_settings
from db.connection import ch_execute, get_db_context, is_clickhouse
from graph.state import TableColumn, TableSchema

settings = get_settings()


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
# Unified helpers (route theo engine của TỪNG domain, không theo active_db)
# ---------------------------------------------------------------------------

async def fetch_all_tables(domain: str) -> list[str]:
    if is_clickhouse(domain):
        return await _ch_fetch_all_tables(domain)
    return await _pg_fetch_all_tables(domain)


async def fetch_table_schema(domain: str, table_name: str) -> TableSchema:
    if is_clickhouse(domain):
        return await _ch_fetch_table_schema(domain, table_name)
    return await _pg_fetch_table_schema(domain, table_name)


