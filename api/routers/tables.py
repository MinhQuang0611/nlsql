import logging
import pandas as pd
from typing import Dict
from fastapi import APIRouter, HTTPException, Query
from agents.schema_agent import _fetch_all_tables
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tables", tags=["Tables"])

# Cache the mapping per domain
_TABLE_MAPPING_CACHE: Dict[str, Dict[str, str]] = {}

def get_table_mapping(domain: str) -> Dict[str, str]:
    global _TABLE_MAPPING_CACHE
    if domain in _TABLE_MAPPING_CACHE:
        return _TABLE_MAPPING_CACHE[domain]

    mapping = {}
    excel_file = f"{domain.upper()}_FINAL.xlsx"
    if not os.path.exists(excel_file):
        logger.warning(f"Metadata file {excel_file} not found. Returning empty mapping.")
        _TABLE_MAPPING_CACHE[domain] = mapping
        return mapping

    try:
        # Không fillna toàn bộ để giữ nguyên NaN, kiểm tra từng ô chính xác hơn
        df = pd.read_excel(excel_file, sheet_name="Database Schema")

        for _, row in df.iterrows():
            ten_bang = row.get("Tên bảng")
            thuoc_tinh = row.get("Tên thuộc tính")
            tieng_viet = row.get("Tên tiếng Việt")

            # Dòng header của bảng: Tên bảng không rỗng VÀ Tên thuộc tính == "--- BẢNG ---"
            ten_bang_str = str(ten_bang).strip() if pd.notna(ten_bang) else ""
            thuoc_tinh_str = str(thuoc_tinh).strip() if pd.notna(thuoc_tinh) else ""
            tieng_viet_str = str(tieng_viet).strip() if pd.notna(tieng_viet) else ""

            if thuoc_tinh_str == "--- BẢNG ---" and ten_bang_str:
                mapping[ten_bang_str] = tieng_viet_str
                logger.debug("Table mapping [%s]: %s → %s", domain, ten_bang_str, tieng_viet_str)

    except Exception as e:
        logger.error(f"Failed to load Excel metadata for {domain}: {e}")

    _TABLE_MAPPING_CACHE[domain] = mapping
    return mapping

@router.get("", response_model=Dict[str, str])
async def list_tables(domain: str = Query("qldt", description="Database domain (qldt or tcns)")):
    logger.info(f"Fetching all available tables for domain: {domain}")
    try:
        tables = await _fetch_all_tables(domain)
        mapping = get_table_mapping(domain)
        
        result = {}
        for table in tables:
            result[table] = mapping.get(table, "")
            
        return result
    except Exception as e:
        logger.error(f"Error fetching tables: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
