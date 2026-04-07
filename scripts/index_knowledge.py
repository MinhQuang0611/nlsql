"""
scripts/index_knowledge.py

Script tự động lấy nội dung từ Google Sheet knowledge base
và index vào Qdrant collection 'knowledge_collection'.

Cấu trúc Sheet ("Trang tính 1") kỳ vọng:
  Cột A: Tiêu đề  (bắt buộc)
  Cột B: Nội dung (bắt buộc)
  Cột C: Nguồn   (tuỳ chọn — tên tài liệu, bộ phận phụ trách...)

Cách dùng:
  python scripts/index_knowledge.py                  # sync từ Sheet
  python scripts/index_knowledge.py --force          # xoá collection cũ và index lại toàn bộ
"""

import argparse
import hashlib
import logging
import sys
import os
from datetime import datetime, timezone

# Thêm project root vào path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import gspread
from google.oauth2.service_account import Credentials
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# ── Constants ────────────────────────────────────────────────────────────────
COLLECTION_NAME = "knowledge_collection"
VECTOR_SIZE = 1536          # text-embedding-3-small
SHEET_ID = settings.sheets_knowledge_id
SHEET_NAME = settings.sheets_knowledge_name
CREDENTIALS_FILE = os.path.abspath(settings.google_sheets_credentials_file)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


# ── Google Sheets ─────────────────────────────────────────────────────────────

def fetch_sheet_rows() -> list[dict]:
    """Lấy tất cả hàng dữ liệu từ Google Sheet."""
    logger.info("Kết nối Google Sheets (spreadsheet_id=%s)...", SHEET_ID)
    credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    gc = gspread.authorize(credentials)

    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(SHEET_NAME)

    all_values = ws.get_all_values()
    if not all_values:
        logger.warning("Sheet trống.")
        return []

    headers = [h.strip() for h in all_values[0]]
    rows = []
    for i, row in enumerate(all_values[1:], start=2):  # bỏ header
        # Pad row nếu thiếu cột
        padded = row + [""] * (len(headers) - len(row))
        data = {headers[j]: padded[j].strip() for j in range(len(headers))}

        title = data.get("Tiêu đề", "") or data.get("Title", "") or ""
        content = data.get("Nội dung", "") or data.get("Content", "") or ""
        source = data.get("Nguồn", "") or data.get("Source", "") or ""

        if not title and not content:
            continue  # bỏ hàng rỗng

        rows.append({
            "sheet_row": i,
            "title": title,
            "content": content,
            "source": source,
            "raw": data,
        })

    logger.info("Đọc được %d hàng từ Sheet.", len(rows))
    return rows


# ── Qdrant helpers ────────────────────────────────────────────────────────────

def ensure_collection(qdrant: QdrantClient, force: bool = False) -> None:
    """Tạo collection nếu chưa có; nếu force=True thì xoá và tạo lại."""
    existing = [c.name for c in qdrant.get_collections().collections]

    if COLLECTION_NAME in existing:
        if force:
            logger.info("--force: Xoá collection '%s' cũ...", COLLECTION_NAME)
            qdrant.delete_collection(COLLECTION_NAME)
        else:
            logger.info("Collection '%s' đã tồn tại. Sẽ upsert (không xoá).", COLLECTION_NAME)
            return

    logger.info("Tạo collection '%s'...", COLLECTION_NAME)
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )


def row_to_point_id(sheet_row: int) -> int:
    """Dùng số hàng làm ID để upsert idempotent."""
    return sheet_row


def build_embed_text(row: dict) -> str:
    """Tạo chuỗi embed từ title + content."""
    parts = []
    if row["title"]:
        parts.append(row["title"])
    if row["content"]:
        parts.append(row["content"])
    return "\n".join(parts)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(force: bool = False) -> int:
    """
    Sync toàn bộ sheet vào Qdrant.
    Trả về số lượng điểm đã upsert.
    """
    rows = fetch_sheet_rows()
    if not rows:
        logger.warning("Không có dữ liệu để index.")
        return 0

    qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )

    ensure_collection(qdrant, force=force)

    points: list[PointStruct] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for row in rows:
        embed_text = build_embed_text(row)
        vector = embeddings.embed_query(embed_text)

        payload = {
            "title": row["title"],
            "content": row["content"],
            "source": row["source"] or SHEET_NAME,
            "sheet_row": row["sheet_row"],
            "embed_text": embed_text,
            "synced_at": now_iso,
        }

        points.append(PointStruct(
            id=row_to_point_id(row["sheet_row"]),
            vector=vector,
            payload=payload,
        ))
        logger.info("  [%d] %s", row["sheet_row"], row["title"] or row["content"][:60])

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    logger.info("✅ Đã upsert %d điểm vào '%s'.", len(points), COLLECTION_NAME)
    return len(points)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index knowledge từ Google Sheet vào Qdrant")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Xoá collection cũ và index lại toàn bộ (mặc định: upsert/merge)",
    )
    args = parser.parse_args()
    run(force=args.force)
