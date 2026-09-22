"""
Benchmark execution accuracy cho pipeline NL2SQL.

Vì sao cần: mọi thay đổi prompt / model / schema retrieval đều là phỏng đoán nếu
không đo được. Đây là thước đo tối thiểu để so sánh trước-sau.

Chỉ số chính là **execution accuracy** — chuẩn dùng trong Spider/BIRD: chạy cả SQL
do agent sinh lẫn SQL chuẩn (gold), rồi so sánh TẬP KẾT QUẢ. Không so sánh chuỗi SQL,
vì hai câu SQL viết khác nhau vẫn có thể cùng đúng.

Bộ câu hỏi nằm ở `config/benchmark_<domain>.json`:

    [
      {
        "question": "Có bao nhiêu sinh viên đang học?",
        "gold_sql": "SELECT count() FROM `SinhVien` WHERE `trangThaiHoc` = 'DANG_HOC'",
        "note": "tuỳ chọn"
      }
    ]

`gold_sql` có thể bỏ trống — khi đó câu hỏi chỉ được tính vào tỉ lệ chạy được
(execution rate), không tính vào accuracy.

QUAN TRỌNG: bộ benchmark phải TÁCH BIỆT với `config/few_shot_<domain>.json`.
Dùng chung câu hỏi thì điểm số chỉ đo khả năng chép lại ví dụ, không đo năng lực thật.
Script sẽ cảnh báo nếu phát hiện trùng.

Chạy:
    docker exec nlsql_app python -m scripts.run_bennmark
    docker exec nlsql_app python -m scripts.run_bennmark qldt
    docker exec nlsql_app python -m scripts.run_bennmark qldt --limit 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

from config import get_settings
from db.connection import is_clickhouse, ch_execute, get_db_context
from graph.builder import build_graph

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

settings = get_settings()
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


async def _run_sql(domain: str, sql: str) -> list[tuple]:
    """Chạy SQL, trả về list tuple để so sánh tập kết quả."""
    if is_clickhouse(domain):
        rows = await ch_execute(domain, sql)
        return [tuple(r) for r in rows]
    from sqlalchemy import text
    async with get_db_context(domain) as db:
        result = await db.execute(text(sql))
        return [tuple(r) for r in result.fetchall()]


def _normalise(rows: list[tuple]) -> list[tuple]:
    """
    Chuẩn hoá để so sánh: ép mọi giá trị về str, bỏ thứ tự dòng.

    Ép str vì cùng một con số có thể về dưới dạng Decimal / int / float tuỳ driver.
    Bỏ thứ tự vì hai câu SQL cùng đúng có thể trả về khác thứ tự khi không có ORDER BY.
    """
    return sorted(tuple(str(v) for v in row) for row in rows)


def _load_cases(domain: str, limit: int | None) -> list[dict]:
    path = CONFIG_DIR / f"benchmark_{domain}.json"
    if not path.exists():
        print(f"  Không có file benchmark cho domain '{domain}' ({path.name})")
        return []
    cases = json.loads(path.read_text(encoding="utf-8"))

    # Cảnh báo rò rỉ few-shot vào benchmark.
    fs_path = CONFIG_DIR / f"few_shot_{domain}.json"
    if fs_path.exists():
        fs_questions = {
            e["question"].strip().lower()
            for e in json.loads(fs_path.read_text(encoding="utf-8"))
        }
        overlap = [c for c in cases if c["question"].strip().lower() in fs_questions]
        if overlap:
            print(
                f"  CẢNH BÁO: {len(overlap)} câu hỏi benchmark trùng với few-shot. "
                f"Điểm số sẽ bị thổi phồng. Câu trùng: "
                f"{[c['question'] for c in overlap]}"
            )

    return cases[:limit] if limit else cases


async def run_domain(domain: str, limit: int | None) -> dict[str, Any]:
    cases = _load_cases(domain, limit)
    if not cases:
        return {}

    app = build_graph()
    results = []

    print(f"\n{'='*78}\nDOMAIN: {domain}  ({len(cases)} câu hỏi)\n{'='*78}")

    for idx, case in enumerate(cases, 1):
        question = case["question"]
        gold_sql = case.get("gold_sql", "").strip()

        started = time.perf_counter()
        state: dict[str, Any] = {
            "user_query": question,
            "session_id": f"benchmark-{domain}-{idx}",
            "domain": domain,
            "history": [],
        }

        record: dict[str, Any] = {
            "question": question,
            "executed": False,
            "accurate": None,      # None = không có gold_sql để đối chiếu
            "error": None,
            "retry_count": 0,
            "data_retry_count": 0,
        }

        try:
            final = await app.ainvoke(state, config={"configurable": {"thread_id": state["session_id"]}, "recursion_limit": 50})
            record["generated_sql"] = final.get("final_sql", "")
            record["row_count"] = final.get("row_count", 0)
            record["retry_count"] = final.get("retry_count", 0)
            record["data_retry_count"] = final.get("data_retry_count", 0)
            record["executed"] = not final.get("executor_error")
            record["error"] = final.get("executor_error")

            if record["executed"] and gold_sql:
                try:
                    gold_rows = _normalise(await _run_sql(domain, gold_sql))
                    pred_rows = _normalise([
                        tuple(r.values()) for r in final.get("query_result", [])
                    ])
                    record["accurate"] = gold_rows == pred_rows
                    if not record["accurate"]:
                        record["gold_row_count"] = len(gold_rows)
                except Exception as exc:
                    record["error"] = f"gold_sql lỗi: {exc}"
        except Exception as exc:
            record["error"] = str(exc)

        record["latency_s"] = round(time.perf_counter() - started, 1)
        results.append(record)

        if record["accurate"] is True:
            mark = "ĐÚNG"
        elif record["accurate"] is False:
            mark = "SAI "
        elif record["executed"]:
            mark = "CHẠY"
        else:
            mark = "LỖI "
        print(f"[{idx:>2}/{len(cases)}] {mark} {record['latency_s']:>5.1f}s  {question[:56]}")
        if record["error"]:
            print(f"          lỗi: {str(record['error'])[:150]}")
        if record["accurate"] is False:
            print(f"          trả về {record['row_count']} dòng, gold {record.get('gold_row_count')} dòng")
            print(f"          SQL: {' '.join(record['generated_sql'].split())[:180]}")

    total = len(results)
    executed = sum(1 for r in results if r["executed"])
    scored = [r for r in results if r["accurate"] is not None]
    accurate = sum(1 for r in scored if r["accurate"])
    retried = sum(1 for r in results if r["retry_count"] or r["data_retry_count"])

    print(f"\n{'-'*78}")
    print(f"  Chạy được (execution rate) : {executed}/{total} ({executed/total*100:.0f}%)")
    if scored:
        print(f"  Đúng (execution accuracy)  : {accurate}/{len(scored)} ({accurate/len(scored)*100:.0f}%)")
    else:
        print("  Đúng (execution accuracy)  : không đo được — chưa có gold_sql")
    print(f"  Phải retry                 : {retried}/{total}")
    print(f"  Latency trung bình         : {sum(r['latency_s'] for r in results)/total:.1f}s")
    print(f"{'-'*78}")

    return {
        "domain": domain,
        "total": total,
        "executed": executed,
        "scored": len(scored),
        "accurate": accurate,
        "results": results,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark execution accuracy cho NL2SQL")
    parser.add_argument("domains", nargs="*", help="domain cần chạy (mặc định: tất cả)")
    parser.add_argument("--limit", type=int, default=None, help="chỉ chạy N câu đầu")
    parser.add_argument("--out", type=str, default=None, help="ghi kết quả chi tiết ra file JSON")
    args = parser.parse_args()

    targets = args.domains or settings.list_domains()
    summaries = []
    for domain in targets:
        summary = await run_domain(domain, args.limit)
        if summary:
            summaries.append(summary)

    if args.out and summaries:
        Path(args.out).write_text(
            json.dumps(summaries, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\nĐã ghi kết quả chi tiết vào {args.out}")


if __name__ == "__main__":
    asyncio.run(main())
