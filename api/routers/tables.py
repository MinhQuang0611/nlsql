import logging
import pandas as pd
from typing import Dict
from fastapi import APIRouter, HTTPException
from agents.schema_agent import _fetch_all_tables

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tables", tags=["Tables"])

# Cache the mapping
_TABLE_MAPPING_CACHE: Dict[str, str] = {}

def get_table_mapping() -> Dict[str, str]:
    global _TABLE_MAPPING_CACHE
    if _TABLE_MAPPING_CACHE:
        return _TABLE_MAPPING_CACHE
        
    try:
        df = pd.read_excel("QLDT_FINAL.xlsx", sheet_name="Database Schema")
        df = df.fillna("")
        current_table = None
        
        for _, row in df.iterrows():
            thuoc_tinh = str(row.get("Tên thuộc tính", "")).strip()
            ten_bang = str(row.get("Tên bảng", "")).strip()
            tieng_viet = str(row.get("Tên tiếng Việt", "")).strip()
            
            if thuoc_tinh == "--- BẢNG ---" and ten_bang:
                current_table = ten_bang
                _TABLE_MAPPING_CACHE[current_table] = tieng_viet
                
    except Exception as e:
        logger.error(f"Failed to load Excel metadata: {e}")
        
    return _TABLE_MAPPING_CACHE

@router.get("", response_model=Dict[str, str])
async def list_tables():
    logger.info("Fetching all available tables")
    try:
        tables = await _fetch_all_tables()
        mapping = get_table_mapping()
        
        result = {}
        for table in tables:
            result[table] = mapping.get(table, "")
            
        return result
    except Exception as e:
        logger.error(f"Error fetching tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
