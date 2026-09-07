import logging
from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy.future import select
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

from api.models.faq import FAQ
from api.schemas.faq import FAQCreate, FAQUpdate, FAQResponse
from db.connection import get_internal_db_context
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["FAQ"])

COLLECTION_NAME = "faq_collection"

def get_qdrant_client():
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)

def get_embeddings():
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key
    )

def ensure_collection(qdrant: QdrantClient):
    try:
        collections = qdrant.get_collections().collections
        if not any(c.name == COLLECTION_NAME for c in collections):
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
    except Exception as e:
        logger.error(f"Failed to ensure Qdrant collection FAQ: {e}")

@router.on_event("startup")
async def startup_event():
    qdrant = get_qdrant_client()
    ensure_collection(qdrant)

@router.get("/faq", response_model=list[FAQResponse])
async def list_faq():
    async with get_internal_db_context() as db:
        result = await db.execute(select(FAQ))
        faqs = result.scalars().all()
        return faqs

@router.post("/faq", response_model=FAQResponse)
async def create_faq(faq_in: FAQCreate):
    async with get_internal_db_context() as db:
        result = await db.execute(select(FAQ).where(FAQ.cau_hoi == faq_in.cau_hoi))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Câu hỏi FAQ này đã tồn tại.")

        new_faq = FAQ(
            cau_hoi=faq_in.cau_hoi,
            cau_tra_loi=faq_in.cau_tra_loi
        )
        db.add(new_faq)
        await db.commit()
        await db.refresh(new_faq)

        # Upsert to Qdrant
        try:
            qdrant = get_qdrant_client()
            ensure_collection(qdrant)
            embeddings = get_embeddings()
            
            vector = embeddings.embed_query(new_faq.cau_hoi)

            point = PointStruct(
                id=new_faq.id,
                vector=vector,
                payload={
                    "cau_hoi": new_faq.cau_hoi,
                    "cau_tra_loi": new_faq.cau_tra_loi,
                    "updated_at": new_faq.updated_at.isoformat() if hasattr(new_faq, 'updated_at') else None
                }
            )
            qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
            logger.info(f"Upserted FAQ {new_faq.id} to Qdrant")
        except Exception as e:
            logger.error(f"Failed to upsert FAQ to Qdrant: {e}")

        return new_faq

@router.put("/faq/{faq_id}", response_model=FAQResponse)
async def update_faq(faq_in: FAQUpdate, faq_id: str = Path(...)):
    async with get_internal_db_context() as db:
        result = await db.execute(select(FAQ).where(FAQ.id == faq_id))
        faq = result.scalar_one_or_none()
        
        if not faq:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi này.")

        if faq_in.cau_hoi is not None:
            faq.cau_hoi = faq_in.cau_hoi
        if faq_in.cau_tra_loi is not None:
            faq.cau_tra_loi = faq_in.cau_tra_loi
            
        await db.commit()
        await db.refresh(faq)

        # Upsert to Qdrant
        try:
            qdrant = get_qdrant_client()
            ensure_collection(qdrant)
            embeddings = get_embeddings()
            
            vector = embeddings.embed_query(faq.cau_hoi)

            point = PointStruct(
                id=faq.id,
                vector=vector,
                payload={
                    "cau_hoi": faq.cau_hoi,
                    "cau_tra_loi": faq.cau_tra_loi,
                    "updated_at": faq.updated_at.isoformat() if hasattr(faq, 'updated_at') else None
                }
            )
            qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
            logger.info(f"Updated FAQ {faq.id} in Qdrant")
        except Exception as e:
            logger.error(f"Failed to update FAQ in Qdrant: {e}")

        return faq

@router.delete("/faq/{faq_id}")
async def delete_faq(faq_id: str = Path(...)):
    async with get_internal_db_context() as db:
        result = await db.execute(select(FAQ).where(FAQ.id == faq_id))
        faq = result.scalar_one_or_none()
        
        if not faq:
            raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi này.")

        await db.delete(faq)
        await db.commit()
        
        # Delete from Qdrant
        try:
            qdrant = get_qdrant_client()
            qdrant.delete(collection_name=COLLECTION_NAME, points_selector=[faq_id])
            logger.info(f"Deleted FAQ {faq_id} from Qdrant")
        except Exception as e:
            logger.error(f"Failed to delete FAQ from Qdrant: {e}")

        return {"message": "Đã xóa FAQ thành công."}
        
@router.get("/faq/search", response_model=list[FAQResponse])
async def search_faq(q: str = Query(..., min_length=1)):
    """
    Tìm kiếm FAQ bằng Vector Search (Semantic Search)
    """
    try:
        qdrant = get_qdrant_client()
        embeddings = get_embeddings()
        
        vector = embeddings.embed_query(q)
        
        search_result = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=10,
            with_payload=True
        )
        
        results = []
        for hit in search_result:
            # Map payload back to FAQResponse structure
            results.append({
                "id": str(hit.id),
                "cau_hoi": hit.payload.get("cau_hoi"),
                "cau_tra_loi": hit.payload.get("cau_tra_loi"),
                "created_at": hit.payload.get("created_at"),
                "updated_at": hit.payload.get("updated_at")
            })
        return results
    except Exception as e:
        logger.error(f"Failed to search FAQ in Qdrant: {e}")
        # Fallback: search in DB with ILIKE if Qdrant fails
        async with get_internal_db_context() as db:
            from sqlalchemy import or_
            result = await db.execute(
                select(FAQ).where(
                    or_(
                        FAQ.cau_hoi.ilike(f"%{q}%"),
                        FAQ.cau_tra_loi.ilike(f"%{q}%")
                    )
                )
            )
            return result.scalars().all()

