"""
Đọc sheet "Database Schema" của <DOMAIN>_FINAL.xlsx: tên tiếng Việt cho bảng / cột,
gợi ý enum, và KHOÁ NGOẠI khai báo trong cột "Metadata (Khóa ngoại, Enum)".

Khoá ngoại từ Excel quan trọng với ClickHouse: engine không có ràng buộc FK, nên
đây là nguồn duy nhất cho LLM biết bảng nào JOIN với bảng nào qua cột nào.
"""
from __future__ import annotations

import json
import logging
import os
from typing import TypedDict

logger = logging.getLogger(__name__)

_TABLE_MARKER = "--- BẢNG ---"


class ColumnMeta(TypedDict, total=False):
    vi_name: str
    note: str
    fk_table: str
    fk_column: str


class TableMeta(TypedDict, total=False):
    table_desc: str
    module: str
    columns: dict[str, ColumnMeta]


def excel_path_for(domain: str) -> str:
    return f"{domain.upper()}_FINAL.xlsx"


def load_excel_metadata(file_path: str) -> dict[str, TableMeta]:
    if not os.path.exists(file_path):
        logger.warning("Không có file metadata %s — index không có tên tiếng Việt.", file_path)
        return {}
    try:
        import pandas as pd
        df = pd.read_excel(file_path, sheet_name="Database Schema").fillna("")
    except Exception as exc:
        logger.error("Đọc %s thất bại: %s", file_path, exc)
        return {}

    mapping: dict[str, TableMeta] = {}
    current: str | None = None
    for _, row in df.iterrows():
        attr = str(row.get("Tên thuộc tính", "")).strip()
        table = str(row.get("Tên bảng", "")).strip()
        vi = str(row.get("Tên tiếng Việt", "")).strip()
        note = str(row.get("Ghi chú tham chiếu", "")).strip()
        module = str(row.get("Phân hệ", "")).strip()
        meta_raw = str(row.get("Metadata (Khóa ngoại, Enum)", "")).strip()

        if attr == _TABLE_MARKER and table:
            current = table
            mapping[current] = TableMeta(table_desc=vi, module=module, columns={})
            continue
        if not current or not attr:
            continue

        col = ColumnMeta(vi_name=vi, note=note)
        if meta_raw:
            try:
                fk = json.loads(meta_raw).get("foreign_key") or {}
                if fk.get("references_table"):
                    col["fk_table"] = fk["references_table"]
                    col["fk_column"] = fk.get("references_column", "")
            except (json.JSONDecodeError, AttributeError):
                pass
        mapping[current]["columns"][attr] = col

    n_fk = sum(1 for t in mapping.values() for c in t["columns"].values() if c.get("fk_table"))
    logger.info("Excel metadata: %d bảng, %d khoá ngoại (%s)", len(mapping), n_fk, file_path)
    return mapping
