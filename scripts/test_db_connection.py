"""
scripts/test_db_connection.py — Standalone script to verify DB connectivity.

Usage:
    python scripts/test_db_connection.py
    # or
    make test-db
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from db.connection import check_db_connection, engine, get_db_context
from config import get_settings


async def main() -> None:
    settings = get_settings()
    print("=" * 60)
    print("  nlsql — DB Connection Test")
    print("=" * 60)
    print(f"  Host    : {settings.db_host}:{settings.db_port}")
    print(f"  DB      : {settings.db_name}")
    print(f"  User    : {settings.db_user}")
    print(f"  Pool    : {settings.db_pool_size} (max overflow {settings.db_max_overflow})")
    print("-" * 60)

    # 1. Basic ping
    result = await check_db_connection()
    if result["status"] == "ok":
        print(f"Connection OK")
        print(f"    {result['version']}")
    else:
        print(f"Connection FAILED: {result['detail']}")
        sys.exit(1)

    # 2. Check seed tables exist
    print("-" * 60)
    tables = ["categories", "products", "customers", "orders", "order_items", "daily_sales"]
    async with get_db_context() as db:
        for table in tables:
            try:
                row = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = row.scalar()
                status = "" if count > 0 else "⚠️ "
                print(f"  {status} {table:<15} — {count:>5} rows")
            except Exception as exc:
                print(f"  {table:<15} — NOT FOUND ({exc})")

    print("=" * 60)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())