import asyncio
import asynch

async def test():
    for port in [9000, 19000]:
        try:
            print(f"Trying {port}...")
            conn = await asynch.connect(host='192.168.30.28', port=port, user='clickhouse', password='')
            print(f"{port} OK")
            await conn.close()
        except Exception as e:
            print(f"{port} Failed: {e}")

asyncio.run(test())
