import logging
from fastapi import APIRouter, HTTPException, Path, Query
from sqlalchemy.future import select
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

from api.models.business_rule import BusinessRule
from api.schemas.business_rule import BusinessRuleCreate, BusinessRuleUpdate, BusinessRuleResponse
from db.connection import get_internal_db_context
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(tags=["Knowledge"])

COLLECTION_NAME = "knowledge_collection"

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
        logger.error(f"Failed to ensure Qdrant collection: {e}")

@router.on_event("startup")
async def startup_event():
    qdrant = get_qdrant_client()
    ensure_collection(qdrant)

@router.get("/knowledge/search", response_model=list[BusinessRuleResponse])
async def search_knowledge(q: str = Query(..., description="Query for vector search")):
    try:
        qdrant = get_qdrant_client()
        embeddings = get_embeddings()
        
        # Embed the query
        vector = embeddings.embed_query(q)
        
        # Search Qdrant
        response = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=5,
            with_payload=True
        )
        search_results = response.points
        
        # Map to BusinessRuleResponse
        rules = []
        for hit in search_results:
            payload = hit.payload
            rules.append(BusinessRuleResponse(
                id=str(hit.id),
                tu_khoa=payload.get("tu_khoa", ""),
                dinh_nghia_sql_logic=payload.get("dinh_nghia_sql_logic", ""),
                updated_at=payload.get("updated_at", "2024-01-01T00:00:00")
            ))
        return rules
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/knowledge", response_model=list[BusinessRuleResponse])
async def list_knowledge_rules():
    async with get_internal_db_context() as db:
        result = await db.execute(select(BusinessRule))
        rules = result.scalars().all()
        return rules

@router.post("/knowledge", response_model=BusinessRuleResponse)
async def create_knowledge_rule(rule_in: BusinessRuleCreate):
    async with get_internal_db_context() as db:
        # Check if tu_khoa exists
        result = await db.execute(select(BusinessRule).where(BusinessRule.tu_khoa == rule_in.tu_khoa))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Quy định với từ khóa này đã tồn tại.")

        new_rule = BusinessRule(
            tu_khoa=rule_in.tu_khoa,
            dinh_nghia_sql_logic=rule_in.dinh_nghia_sql_logic
        )
        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)

        # Upsert to Qdrant
        try:
            qdrant = get_qdrant_client()
            ensure_collection(qdrant)
            embeddings = get_embeddings()
            
            embed_text = f"Nghiệp vụ: {new_rule.tu_khoa}. Định nghĩa: {new_rule.dinh_nghia_sql_logic}"
            vector = embeddings.embed_query(embed_text)

            point = PointStruct(
                id=new_rule.id,
                vector=vector,
                payload={
                    "tu_khoa": new_rule.tu_khoa,
                    "dinh_nghia_sql_logic": new_rule.dinh_nghia_sql_logic,
                    "updated_at": new_rule.updated_at.isoformat() if hasattr(new_rule, 'updated_at') else None
                }
            )
            qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
            logger.info(f"Upserted rule {new_rule.id} to Qdrant")
        except Exception as e:
            logger.error(f"Failed to upsert to Qdrant: {e}")

        return new_rule

@router.put("/knowledge/{rule_id}", response_model=BusinessRuleResponse)
async def update_knowledge_rule(rule_in: BusinessRuleUpdate, rule_id: str = Path(...)):
    async with get_internal_db_context() as db:
        result = await db.execute(select(BusinessRule).where(BusinessRule.id == rule_id))
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Không tìm thấy quy định này.")

        if rule_in.tu_khoa is not None:
            rule.tu_khoa = rule_in.tu_khoa
        if rule_in.dinh_nghia_sql_logic is not None:
            rule.dinh_nghia_sql_logic = rule_in.dinh_nghia_sql_logic
            
        await db.commit()
        await db.refresh(rule)

        # Upsert to Qdrant
        try:
            qdrant = get_qdrant_client()
            ensure_collection(qdrant)
            embeddings = get_embeddings()
            
            embed_text = f"Nghiệp vụ: {rule.tu_khoa}. Định nghĩa: {rule.dinh_nghia_sql_logic}"
            vector = embeddings.embed_query(embed_text)

            point = PointStruct(
                id=rule.id,
                vector=vector,
                payload={
                    "tu_khoa": rule.tu_khoa,
                    "dinh_nghia_sql_logic": rule.dinh_nghia_sql_logic,
                    "updated_at": rule.updated_at.isoformat() if hasattr(rule, 'updated_at') else None
                }
            )
            qdrant.upsert(collection_name=COLLECTION_NAME, points=[point])
            logger.info(f"Updated rule {rule.id} in Qdrant")
        except Exception as e:
            logger.error(f"Failed to update to Qdrant: {e}")

        return rule

@router.delete("/knowledge/{rule_id}")
async def delete_knowledge_rule(rule_id: str = Path(...)):
    async with get_internal_db_context() as db:
        result = await db.execute(select(BusinessRule).where(BusinessRule.id == rule_id))
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(status_code=404, detail="Không tìm thấy quy định này.")

        await db.delete(rule)
        await db.commit()
        
        # Delete from Qdrant
        try:
            qdrant = get_qdrant_client()
            qdrant.delete(collection_name=COLLECTION_NAME, points_selector=[rule_id])
            logger.info(f"Deleted rule {rule_id} from Qdrant")
        except Exception as e:
            logger.error(f"Failed to delete from Qdrant: {e}")

        return {"message": "Đã xóa quy định thành công."}
