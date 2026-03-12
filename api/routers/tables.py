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
        # Không fillna toàn bộ để giữ nguyên NaN, kiểm tra từng ô chính xác hơn
        df = pd.read_excel("QLDT_FINAL.xlsx", sheet_name="Database Schema")

        for _, row in df.iterrows():
            ten_bang = row.get("Tên bảng")
            thuoc_tinh = row.get("Tên thuộc tính")
            tieng_viet = row.get("Tên tiếng Việt")

            # Dòng header của bảng: Tên bảng không rỗng VÀ Tên thuộc tính == "--- BẢNG ---"
            ten_bang_str = str(ten_bang).strip() if pd.notna(ten_bang) else ""
            thuoc_tinh_str = str(thuoc_tinh).strip() if pd.notna(thuoc_tinh) else ""
            tieng_viet_str = str(tieng_viet).strip() if pd.notna(tieng_viet) else ""

            if thuoc_tinh_str == "--- BẢNG ---" and ten_bang_str:
                _TABLE_MAPPING_CACHE[ten_bang_str] = tieng_viet_str
                logger.debug("Table mapping: %s → %s", ten_bang_str, tieng_viet_str)

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
