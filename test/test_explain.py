import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.connection import ch_execute

async def main():
    try:
        res = await ch_execute("EXPLAIN SELECT nonexistent FROM SinhVien")
        print("EXPLAIN successfully returned:", res)
    except Exception as e:
        print("EXPLAIN failed with exception:", e)

if __name__ == "__main__":
    asyncio.run(main())
