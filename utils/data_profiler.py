"""
utils/data_profiler.py
Phân tích cấu trúc kết quả SQL để xác định kiểu dữ liệu và vai trò của từng cột.
"""
from __future__ import annotations

import re
from typing import Any, Literal

from typing_extensions import TypedDict


# ── Từ khóa liên quan đến ngày/tháng/năm ──────────────────────────────────────
_DATE_KEYWORDS = re.compile(
    r"(date|time|month|year|quarter|week|day|hour|minute|"
    r"ngay|thang|nam|tuan|gio|quy|period|periode)",
    re.IGNORECASE,
)

InferredType = Literal["string", "integer", "float", "date"]
ColumnRole = Literal["dimension", "measure"]


class ColumnProfile(TypedDict):
    col_name: str
    inferred_type: InferredType
    role: ColumnRole
    n_unique: int
    has_nulls: bool


def _infer_type(values: list[Any]) -> InferredType:
    """Thử xác định kiểu số học; fallback về 'string'."""
    non_null = [v for v in values if v is not None and v != ""]
    if not non_null:
        return "string"

    # Thử int
    try:
        [int(v) for v in non_null]
        return "integer"
    except (ValueError, TypeError):
        pass

    # Thử float
    try:
        [float(v) for v in non_null]
        return "float"
    except (ValueError, TypeError):
        pass

    return "string"


def profile_columns(rows: list[dict[str, Any]]) -> list[ColumnProfile]:
    """
    Phân tích danh sách các hàng SQL và trả về profile cho từng cột.

    Args:
        rows: Danh sách dict (query_result từ database).

    Returns:
        list[ColumnProfile] — mỗi phần tử mô tả một cột.
    """
    if not rows:
        return []

    columns = list(rows[0].keys())
    profiles: list[ColumnProfile] = []

    for col in columns:
        values = [row.get(col) for row in rows]
        non_null_values = [v for v in values if v is not None and v != ""]
        has_nulls = len(non_null_values) < len(values)
        unique_vals = set(str(v) for v in non_null_values)
        n_unique = len(unique_vals)

        # Kiểm tra tên cột có liên quan đến thời gian không
        if _DATE_KEYWORDS.search(col):
            inferred_type: InferredType = "date"
            role: ColumnRole = "dimension"
        else:
            inferred_type = _infer_type(non_null_values)
            # dimension: string hoặc date; measure: integer/float
            if inferred_type in ("integer", "float"):
                role = "measure"
            else:
                role = "dimension"

        profiles.append(
            ColumnProfile(
                col_name=col,
                inferred_type=inferred_type,
                role=role,
                n_unique=n_unique,
                has_nulls=has_nulls,
            )
        )

    return profiles


def format_profile_for_prompt(profiles: list[ColumnProfile]) -> str:
    """
    Tạo chuỗi mô tả ngắn gọn để nhúng vào LLM prompt.

    Ví dụ:
        - nganh: string (dimension, 3 giá trị duy nhất)
        - so_luong: integer (measure, 3 giá trị duy nhất)
    """
    lines = []
    for p in profiles:
        null_note = " — có giá trị null" if p["has_nulls"] else ""
        lines.append(
            f"  - {p['col_name']}: {p['inferred_type']}"
            f" ({p['role']}, {p['n_unique']} giá trị duy nhất{null_note})"
        )
    return "\n".join(lines)
