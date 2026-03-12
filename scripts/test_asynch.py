import sys
import pprint

try:
    import asynch
    print("ASYNCH IMPORTED")
    print(dir(asynch))
    if hasattr(asynch, '__version__'):
        print("VERSION:", asynch.__version__)
except Exception as e:
    print("ERROR IMPORTING:", e)
    
try:
    from clickhouse_sqlalchemy.drivers.asynch.base import AsyncAdapt_asynch_cursor
    async def _async_soft_close(self):
        pass
    AsyncAdapt_asynch_cursor._async_soft_close = _async_soft_close
    print("PATCH APPLIED SUCCESSFULLY")
    
    from sqlalchemy.ext.asyncio import create_async_engine
    e = create_async_engine('clickhouse+asynch://default:@localhost:9000/nlsql')
    print("ENGINE CREATED:", e)
except Exception as e:
    print("ERROR ENGINE:", e)
