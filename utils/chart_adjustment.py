"""
utils/chart_adjustment.py
Tinh chỉnh chart_data và chart_config sau khi LLM đưa ra quyết định chart type:
  1. Sắp xếp giảm dần theo y_axis (cho bar/pie).
  2. Gán nhãn trục x/y nếu LLM để null.
  3. Gộp các nhóm nhỏ (< other_threshold % tổng) thành "Khác" (cho bar/pie).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Ngưỡng mặc định: nhóm chiếm < 2% tổng sẽ bị gộp vào "Khác"
DEFAULT_OTHER_THRESHOLD_PCT: float = 2.0

# Chỉ sort & group khi chart thuộc các loại này
_SORTABLE_CHART_TYPES = {"bar", "pie"}


def _coerce_numeric(value: Any) -> Optional[float]:
    """Ép kiểu sang float, trả None nếu thất bại."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def adjust_chart_data(
    chart_data: list[dict[str, Any]],
    chart_config: dict[str, Any],
    profiles: list[dict[str, Any]],
    other_threshold_pct: float = DEFAULT_OTHER_THRESHOLD_PCT,
    sort_desc: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Hậu xử lý chart_data và chart_config.

    Args:
        chart_data: Dữ liệu đã được reshape bởi _reshape_for_chart().
        chart_config: Dict config từ LLM (có thể thiếu x_label/y_label).
        profiles: Output của profile_columns() — dùng để gán nhãn trục.
        other_threshold_pct: Nhóm có tỷ lệ < X% tổng sẽ bị gộp thành "Khác".
        sort_desc: Nếu True, sắp xếp giảm dần theo y.

    Returns:
        (adjusted_chart_data, updated_chart_config)
    """
    if not chart_data:
        return chart_data, chart_config

    chart_type = chart_config.get("chart_type", "table")
    config = dict(chart_config)  # không mutate bản gốc

    # ── 1. Gán nhãn trục nếu LLM để null ─────────────────────────────────────
    if not config.get("x_label"):
        x_axis = config.get("x_axis")
        if x_axis:
            config["x_label"] = x_axis

    if not config.get("y_label"):
        y_axis = config.get("y_axis")
        if y_axis:
            config["y_label"] = y_axis

    # Chỉ sắp xếp và gộp nhóm cho bar / pie
    if chart_type not in _SORTABLE_CHART_TYPES:
        return chart_data, config

    # ── 2. Sắp xếp giảm dần theo trục Y ──────────────────────────────────────
    data: list[dict[str, Any]] = list(chart_data)
    if sort_desc:
        def sort_key(row: dict[str, Any]) -> float:
            num = _coerce_numeric(row.get("y"))
            return num if num is not None else 0.0

        data.sort(key=sort_key, reverse=True)
        logger.debug("[ChartAdjustment] sorted %d rows desc by y", len(data))

    # ── 3. Gộp nhóm nhỏ thành "Khác" ─────────────────────────────────────────
    if other_threshold_pct > 0:
        nums = [_coerce_numeric(row.get("y")) for row in data]
        total = sum(n for n in nums if n is not None)

        if total > 0:
            threshold_value = total * other_threshold_pct / 100.0
            keep: list[dict[str, Any]] = []
            other_sum = 0.0
            other_count = 0

            for row in data:
                y_val = _coerce_numeric(row.get("y"))
                if y_val is not None and y_val < threshold_value:
                    other_sum = other_sum + y_val
                    other_count = other_count + 1
                else:
                    keep.append(row)

            if other_count > 0:
                sample_row = keep[0] if keep else data[0]
                other_row: dict[str, Any] = {k: None for k in sample_row}
                other_row["x"] = "Khác"
                other_row["y"] = other_sum

                x_axis_col = config.get("x_axis")
                y_axis_col = config.get("y_axis")
                if x_axis_col:
                    other_row[x_axis_col] = "Khác"
                if y_axis_col:
                    other_row[y_axis_col] = other_sum

                keep.append(other_row)
                logger.debug(
                    "[ChartAdjustment] grouped %d small rows into 'Khác' (sum=%.2f, threshold=%.2f%%)",
                    other_count, other_sum, other_threshold_pct,
                )

            data = keep

    return data, config
