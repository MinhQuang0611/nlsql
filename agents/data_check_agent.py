"""
Kiểm định KẾT QUẢ sau khi chạy SQL (execution-guided self-correction).

Vòng lặp sửa lỗi hiện có chỉ dừng ở `sql_check_agent`: EXPLAIN kiểm tra cú pháp và
quyền truy cập. Một câu SQL sai ngữ nghĩa — JOIN nhầm khoá, WHERE lọc nhầm giá trị
enum, ép kiểu sai — vẫn qua EXPLAIN trót lọt rồi trả về 0 dòng hoặc toàn NULL, và
người dùng nhận một câu trả lời sai mà hệ thống tưởng là thành công.

Node này đóng vòng lặp đó: đọc kết quả thật, phán đoán nó có hợp lý không, và nếu
không thì đẩy ngược về sql_gen kèm lý do cụ thể.

Lưu ý quan trọng: **0 dòng không phải lúc nào cũng là lỗi.** "Có sinh viên nào GPA
trên 3.99 không?" trả về 0 dòng là câu trả lời đúng. Vì vậy 0 dòng chỉ được retry
ĐÚNG MỘT LẦN (`MAX_DATA_RETRY`), sau đó chấp nhận kết quả — retry mù chỉ đốt token
và có thể sinh ra SQL sai hơn bản đầu.
"""
from __future__ import annotations

import logging
from typing import Any

from graph.state import AgentState

logger = logging.getLogger(__name__)

# 0 dòng / toàn NULL chỉ đáng thử lại một lần.
MAX_DATA_RETRY = 1


def _all_values_null(rows: list[dict[str, Any]]) -> bool:
    """True nếu mọi ô trong mọi dòng đều NULL."""
    if not rows:
        return False
    for row in rows:
        for value in row.values():
            if value is not None:
                return False
    return True


def _is_null_scalar(rows: list[dict[str, Any]]) -> bool:
    """True nếu kết quả là đúng một ô duy nhất và ô đó NULL (aggregate hỏng)."""
    if len(rows) != 1:
        return False
    values = list(rows[0].values())
    return len(values) == 1 and values[0] is None


async def data_check_agent(state: AgentState) -> dict:
    """
    LangGraph node: kiểm định kết quả thực thi.
    Đọc : query_result, row_count, executor_error, data_retry_count
    Ghi  : data_check_is_valid, data_check_issues
    """
    rows = state.get("query_result", []) or []
    row_count = state.get("row_count", 0)
    executor_error = state.get("executor_error")
    data_retry_count = state.get("data_retry_count", 0)
    final_sql = state.get("final_sql", "")

    issues: list[str] = []

    # 1. Lỗi thực thi — luôn đáng sửa, thông báo lỗi của DB là gợi ý tốt nhất.
    if executor_error:
        issues.append(
            f"Câu SQL chạy lỗi trên database: {executor_error}. "
            f"Hãy sửa lại dựa trên thông báo lỗi này."
        )

    # 2. Không có dòng nào.
    elif row_count == 0:
        issues.append(
            "Câu SQL chạy được nhưng trả về 0 dòng. Nguyên nhân thường gặp: "
            "JOIN sai khoá (ví dụ dùng `_id` thay vì khoá nghiệp vụ), "
            "điều kiện WHERE so sánh với giá trị enum không tồn tại, "
            "hoặc lọc theo khoảng thời gian không có dữ liệu. "
            "Hãy rà lại điều kiện JOIN và WHERE. "
            "Nếu bạn xác định 0 dòng CHÍNH LÀ câu trả lời đúng, giữ nguyên câu SQL."
        )

    # 3. Có dòng nhưng toàn NULL — thường là JOIN hỏng hoặc chọn nhầm cột.
    elif _is_null_scalar(rows):
        issues.append(
            "Kết quả là một giá trị tổng hợp duy nhất và giá trị đó là NULL. "
            "Thường do aggregate chạy trên cột sai hoặc trên tập rỗng sau JOIN. "
            "Hãy kiểm tra lại cột được aggregate và điều kiện JOIN."
        )
    elif _all_values_null(rows):
        issues.append(
            f"Cả {row_count} dòng trả về đều có toàn bộ giá trị NULL. "
            "Nhiều khả năng JOIN sai khoá nên không khớp được dòng nào, "
            "hoặc đang SELECT nhầm cột. Hãy kiểm tra lại điều kiện JOIN."
        )

    is_valid = not issues

    if is_valid:
        logger.info("[DataCheckAgent] PASS — %d dòng, dữ liệu hợp lệ.", row_count)
    elif data_retry_count >= MAX_DATA_RETRY:
        # Hết lượt: chấp nhận kết quả và để answer_agent diễn giải trung thực.
        logger.warning(
            "[DataCheckAgent] Vẫn còn vấn đề sau %d lần thử lại — chấp nhận kết quả. issues=%s",
            data_retry_count, issues,
        )
        is_valid = True
    else:
        logger.warning(
            "[DataCheckAgent] FAIL (lần %d/%d) — đẩy lại sql_gen. issues=%s\nSQL:\n%s",
            data_retry_count + 1, MAX_DATA_RETRY, issues, final_sql,
        )

    return {
        "data_check_is_valid": is_valid,
        "data_check_issues": issues,
    }
