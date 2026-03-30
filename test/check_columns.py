import asyncio, sys, os
sys.path.insert(0, r"e:\code\text2dashboard\nl_sql")
from db.connection import engine
from sqlalchemy import text

async def main():
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'SinhVien'"))
            cols = [r[0] for r in res.fetchall()]
            print("Columns in SinhVien:", cols)
            
            res2 = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'KqhtTichLuy'"))
            cols2 = [r[0] for r in res2.fetchall()]
            print("Columns in KqhtTichLuy:", cols2)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
