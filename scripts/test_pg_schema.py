import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.introspect import fetch_all_tables as _fetch_all_tables, fetch_table_schema as _fetch_table_schema

async def main():
    try:
        tables = await _fetch_all_tables()
        print(f"Tables found: {tables}")
        for t in tables[:2]:  # Test first 2 tables
            schema = await _fetch_table_schema(t)
            print(f"Schema for {t}:")
            print(f"  Description: {schema['description']}")
            print(f"  Columns: {[c['name'] for c in schema['columns']]}")
            print(f"  Sample rows: {len(schema['sample_rows'])}")
    except Exception as e:
        print(f"Error checking PostgreSQL schema: {e}")

if __name__ == "__main__":
    asyncio.run(main())
