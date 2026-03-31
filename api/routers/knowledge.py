"""
api/routers/knowledge.py

Các endpoint quản lý Knowledge Base:

POST /api/v1/knowledge/sync       — Sync toàn bộ từ Google Sheet vào Qdrant
POST /api/v1/knowledge/add        — Thêm 1 entry thủ công
GET  /api/v1/knowledge/list       — Xem danh sách entries (có filter + pagination)
DELETE /api/v1/knowledge/{id}     — Xoá 1 entry theo ID
"""

from __future__ import annotations

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])

COLLECTION_NAME = "knowledge_collection"
VECTOR_SIZE = 1536


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class KnowledgeAddRequest(BaseModel):
    title: str = Field(..., description="Tiêu đề / chủ đề của mục kiến thức")
    content: str = Field(..., description="Nội dung kiến thức chi tiết")
    source: str = Field(default="manual", description="Nguồn gốc (tên tài liệu, bộ phận...)")


class KnowledgeEntry(BaseModel):
    id: int
    title: str
    content: str
    source: str
    synced_at: Optional[str] = None


class SyncResponse(BaseModel):
    status: str
    indexed: int
    message: str


class AddResponse(BaseModel):
    status: str
    id: int
    message: str


class ListResponse(BaseModel):
    total: int
    items: list[KnowledgeEntry]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_qdrant() -> QdrantClient:
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


def _ensure_collection(qdrant: QdrantClient) -> None:
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in existing:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        logger.info("[Knowledge] Đã tạo collection '%s'.", COLLECTION_NAME)


def _next_id(qdrant: QdrantClient) -> int:
    """Lấy ID tiếp theo bằng cách lấy count hiện tại + offset an toàn."""
    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        return (info.points_count or 0) + 10_000  # offset tránh trùng với sheet rows
    except Exception:
        return 10_001


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/sync", response_model=SyncResponse)
async def sync_from_sheet(background_tasks: BackgroundTasks, force: bool = Query(default=False, description="Xoá và rebuild hoàn toàn")) -> SyncResponse:
    """
    Đồng bộ toàn bộ kiến thức từ Google Sheet vào Qdrant.
    Thao tác chạy **sync** (blocking) để trả về kết quả ngay.
    Dùng `force=true` để xoá collection cũ và index lại sạch từ đầu.
    """
    try:
        # Import và chạy trong thread (tránh block event loop vì gspread + embed)
        from scripts.index_knowledge import run as _run
        indexed = await asyncio.to_thread(_run, force)
        return SyncResponse(
            status="ok",
            indexed=indexed,
            message=f"Đã đồng bộ {indexed} mục kiến thức từ Google Sheet.",
        )
    except Exception as exc:
        logger.error("[Knowledge/sync] Lỗi: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/add", response_model=AddResponse)
async def add_knowledge(body: KnowledgeAddRequest) -> AddResponse:
    """
    Thêm thủ công 1 mục kiến thức vào collection.
    Entry này sẽ được merge cùng với dữ liệu từ Sheet (không bị overwrite khi sync).
    """
    try:
        qdrant = _get_qdrant()
        embeddings = _get_embeddings()
        _ensure_collection(qdrant)

        embed_text = f"{body.title}\n{body.content}".strip()
        vector = await asyncio.to_thread(embeddings.embed_query, embed_text)

        new_id = _next_id(qdrant)
        now_iso = datetime.now(timezone.utc).isoformat()

        point = PointStruct(
            id=new_id,
            vector=vector,
            payload={
                "title": body.title,
                "content": body.content,
                "source": body.source,
                "embed_text": embed_text,
                "synced_at": now_iso,
            },
        )

        await asyncio.to_thread(qdrant.upsert, collection_name=COLLECTION_NAME, points=[point])
        logger.info("[Knowledge/add] Thêm entry id=%d: %r", new_id, body.title)

        return AddResponse(
            status="ok",
            id=new_id,
            message=f"Đã thêm mục kiến thức '{body.title}' (id={new_id}).",
        )
    except Exception as exc:
        logger.error("[Knowledge/add] Lỗi: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/list", response_model=ListResponse)
async def list_knowledge(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None, description="Tìm kiếm theo tiêu đề/nội dung (semantic)"),
) -> ListResponse:
    """
    Liệt kê các mục kiến thức trong collection.
    Nếu truyền `search`, sẽ tìm kiếm semantic và trả về kết quả theo score.
    """
    try:
        qdrant = _get_qdrant()
        _ensure_collection(qdrant)

        if search:
            embeddings = _get_embeddings()
            vector = await asyncio.to_thread(embeddings.embed_query, search)
            results = qdrant.query_points(
                collection_name=COLLECTION_NAME,
                query=vector,
                limit=limit,
                with_payload=True,
            ).points

            items = []
            for hit in results:
                p = hit.payload or {}
                items.append(KnowledgeEntry(
                    id=hit.id if isinstance(hit.id, int) else 0,
                    title=p.get("title", ""),
                    content=p.get("content", ""),
                    source=p.get("source", ""),
                    synced_at=p.get("synced_at"),
                ))
            return ListResponse(total=len(items), items=items)

        # Scroll (không search)
        scroll_result = qdrant.scroll(
            collection_name=COLLECTION_NAME,
            offset=offset,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        points, _ = scroll_result
        items = []
        for pt in points:
            p = pt.payload or {}
            items.append(KnowledgeEntry(
                id=pt.id if isinstance(pt.id, int) else 0,
                title=p.get("title", ""),
                content=p.get("content", ""),
                source=p.get("source", ""),
                synced_at=p.get("synced_at"),
            ))

        total_info = qdrant.get_collection(COLLECTION_NAME)
        total = total_info.points_count or len(items)

        return ListResponse(total=total, items=items)

    except Exception as exc:
        logger.error("[Knowledge/list] Lỗi: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/{entry_id}", response_model=dict)
async def delete_knowledge(entry_id: int) -> dict:
    """Xoá 1 mục kiến thức theo ID."""
    try:
        qdrant = _get_qdrant()
        _ensure_collection(qdrant)
        from qdrant_client.http.models import PointIdsList
        qdrant.delete(
            collection_name=COLLECTION_NAME,
            points_selector=PointIdsList(points=[entry_id]),
        )
        logger.info("[Knowledge/delete] Đã xoá entry id=%d", entry_id)
        return {"status": "ok", "message": f"Đã xoá mục id={entry_id}."}
    except Exception as exc:
        logger.error("[Knowledge/delete] Lỗi: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
