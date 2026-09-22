"""
Index schema vào Qdrant theo HAI TẦNG cho mỗi domain:

  schema_collection_<domain>   — một điểm / bảng. Text embed NGẮN (tên + mô tả tiếng Việt),
                                 payload chứa schema_json đầy đủ (cột + tên TV + FK Excel +
                                 sample) và row_count.
  schema_columns_<domain>      — một điểm / cột nghiệp vụ. Text = "Tên TV (col) — bảng X (mô tả)".

Vì sao hai tầng: bản cũ nhét MỌI cột vào một đoạn văn dài rồi embed. Câu hỏi
"Tổng số sinh viên" khi đó khớp `DotXtnSinhVien`, `HeSoQuyMoLop` (nhiều cột chứa
"sinh viên") hơn chính bảng `SinhVien` — bảng đúng đứng hạng 18/253. Tách cột ra
điểm riêng thì bảng được kéo lên nhờ cột khớp nhất ("trạng thái học" → `trangThaiHoc`)
mà không bị pha loãng bởi số lượng cột.

Chạy:  python -m scripts.index_schema              # bỏ qua domain đã index đúng version
       python -m scripts.index_schema qldt --force # index lại
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from typing import Any

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointStruct, VectorParams
from sqlalchemy import text

from db.introspect import fetch_all_tables, fetch_table_schema
from config import get_settings
from db.connection import ch_execute, get_db_context, is_clickhouse
from utils.excel_metadata import excel_path_for, load_excel_metadata
from utils.text_norm import split_camel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()

# Tăng khi đổi cấu trúc payload / cách embed — startup sẽ tự index lại.
INDEX_VERSION = 2
_EMBED_BATCH = 128

# Cột kỹ thuật: vẫn nằm trong schema_json, nhưng không tạo điểm riêng (chỉ gây nhiễu).
_TECH_COLUMNS = {"_id", "id", "createdAt", "updatedAt", "deletedAt", "active", "deleted",
                 "isDeleted", "createdBy", "updatedBy", "__v"}


def table_collection(domain: str) -> str:
    return f"schema_collection_{domain}"


def column_collection(domain: str) -> str:
    return f"schema_columns_{domain}"


async def _row_count(domain: str, table: str) -> int:
    try:
        if is_clickhouse(domain):
            rows = await ch_execute(domain, f"SELECT count() FROM `{table}`")
            return int(rows[0][0]) if rows else 0
        async with get_db_context(domain) as db:
            r = await db.execute(text("SELECT reltuples::bigint FROM pg_class WHERE relname = :t"), {"t": table})
            v = r.scalar()
            return max(int(v or 0), 0)
    except Exception as exc:
        logger.warning("row_count(%s.%s) lỗi: %s", domain, table, exc)
        return 0


def _merge_excel(schema: dict, meta: dict) -> None:
    """Gắn tên TV / ghi chú / FK từ Excel vào TableSchema (in-place)."""
    if meta.get("table_desc"):
        schema["excel_table_desc"] = meta["table_desc"]
    col_meta = meta.get("columns", {})
    existing_fk = {(fk["column_name"], fk["foreign_table"]) for fk in schema.get("foreign_keys") or []}
    fks = list(schema.get("foreign_keys") or [])
    for c in schema["columns"]:
        m = col_meta.get(c["name"])
        if not m:
            continue
        if m.get("vi_name"):
            c["excel_vi_name"] = m["vi_name"]
        if m.get("note"):
            c["excel_note"] = m["note"]
        if m.get("fk_table") and (c["name"], m["fk_table"]) not in existing_fk:
            fks.append({"column_name": c["name"], "foreign_table": m["fk_table"],
                        "foreign_column": m.get("fk_column", "")})
    schema["foreign_keys"] = fks


def _table_text(name: str, desc: str, module: str) -> str:
    words = split_camel(name)
    parts = [f"Bảng {name} ({words})"]
    if desc:
        parts.append(f"lưu thông tin về {desc}")
    if module:
        parts.append(f"thuộc phân hệ {module}")
    return ". ".join(parts) + "."


def _column_text(col: str, vi: str, table: str, desc: str) -> str:
    label = f"{vi} ({col})" if vi else f"{col} ({split_camel(col)})"
    where = f"bảng {table}" + (f" — {desc}" if desc else "")
    return f"{label}, thuộc {where}."


def _json_safe(obj: Any) -> Any:
    return json.loads(json.dumps(obj, default=str, ensure_ascii=False))


def _ensure_collection(qdrant: QdrantClient, name: str) -> None:
    if qdrant.collection_exists(name):
        qdrant.delete_collection(name)
    qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(size=settings.embedding_dimensions, distance=Distance.COSINE),
    )


def is_indexed(qdrant: QdrantClient, domain: str) -> bool:
    """True nếu domain đã có index đúng INDEX_VERSION."""
    name = table_collection(domain)
    if not qdrant.collection_exists(name) or not qdrant.collection_exists(column_collection(domain)):
        return False
    pts, _ = qdrant.scroll(name, limit=1, with_payload=True, with_vectors=False)
    return bool(pts) and pts[0].payload.get("index_version") == INDEX_VERSION


def _embed_batches(embeddings: OpenAIEmbeddings, texts: list[str]) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), _EMBED_BATCH):
        out.extend(embeddings.embed_documents(texts[i:i + _EMBED_BATCH]))
    return out


async def index_domain(domain: str, qdrant: QdrantClient, embeddings: OpenAIEmbeddings) -> tuple[int, int]:
    all_tables = await fetch_all_tables(domain)
    logger.info("[%s] %d bảng trong DB", domain, len(all_tables))
    if not all_tables:
        return 0, 0

    excel = load_excel_metadata(excel_path_for(domain))

    table_points: list[PointStruct] = []
    table_texts: list[str] = []
    col_payloads: list[dict] = []
    col_texts: list[str] = []

    for idx, tname in enumerate(all_tables):
        schema = await fetch_table_schema(domain, tname)
        meta = excel.get(tname, {})
        _merge_excel(schema, meta)
        desc = meta.get("table_desc", "") or schema.get("description") or ""
        module = meta.get("module", "")
        row_count = await _row_count(domain, tname)

        # Sample chỉ giữ 1 dòng, cắt chuỗi dài — payload không phải chỗ chứa dữ liệu.
        if schema.get("sample_rows"):
            sample = {k: (str(v)[:60] if v is not None else None) for k, v in schema["sample_rows"][0].items()}
            schema["sample_rows"] = [sample]

        table_texts.append(_table_text(tname, desc, module))
        table_points.append(PointStruct(
            id=idx + 1, vector=[],  # vector gán sau khi embed batch
            payload={
                "index_version": INDEX_VERSION,
                "table_name": tname,
                "table_desc": desc,
                "module": module,
                "row_count": row_count,
                "n_columns": len(schema["columns"]),
                "fk_tables": sorted({fk["foreign_table"] for fk in schema.get("foreign_keys") or []}),
                "schema_json": json.dumps(_json_safe(schema), ensure_ascii=False),
            },
        ))

        for c in schema["columns"]:
            if c["name"] in _TECH_COLUMNS:
                continue
            vi = c.get("excel_vi_name", "")
            col_texts.append(_column_text(c["name"], vi, tname, desc))
            col_payloads.append({
                "index_version": INDEX_VERSION,
                "table_name": tname,
                "column_name": c["name"],
                "vi_name": vi,
            })
        logger.info("[%s] %s — %d cột, %d dòng", domain, tname, len(schema["columns"]), row_count)

    logger.info("[%s] embedding %d bảng + %d cột…", domain, len(table_texts), len(col_texts))
    for p, v in zip(table_points, _embed_batches(embeddings, table_texts)):
        p.vector = v
    col_points = [
        PointStruct(id=i + 1, vector=v, payload=pl)
        for i, (v, pl) in enumerate(zip(_embed_batches(embeddings, col_texts), col_payloads))
    ]

    _ensure_collection(qdrant, table_collection(domain))
    qdrant.upsert(collection_name=table_collection(domain), points=table_points)
    _ensure_collection(qdrant, column_collection(domain))
    for i in range(0, len(col_points), 512):
        qdrant.upsert(collection_name=column_collection(domain), points=col_points[i:i + 512])

    logger.info("[%s] xong: %d bảng, %d cột.", domain, len(table_points), len(col_points))
    return len(table_points), len(col_points)


async def main(domains: list[str] | None = None, force: bool = False) -> None:
    domains = domains or settings.list_domains()
    qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)

    for domain in domains:
        if not force and is_indexed(qdrant, domain):
            logger.info("[%s] đã có index version %d — bỏ qua (dùng --force để index lại).", domain, INDEX_VERSION)
            continue
        try:
            await index_domain(domain, qdrant, embeddings)
        except Exception as exc:
            logger.error("[%s] index thất bại: %s", domain, exc, exc_info=True)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    asyncio.run(main(args or None, force="--force" in sys.argv))
