import asyncio
import logging

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

from config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

COLLECTION_NAME = "few_shot_collection"

# Sample few-shot pairs. The user can expand this list with 20-30 real queries.
FEW_SHOT_EXAMPLES = [
    {
        "question": "Lấy danh sách top 5 khách hàng mua nhiều nhất?",
        "sql": 'SELECT "customer_id", SUM("total_amount") as total_spent FROM "orders" GROUP BY "customer_id" ORDER BY total_spent DESC LIMIT 5'
    },
    {
        "question": "Có bao nhiêu đơn hàng được tạo trong tháng 10 năm nay?",
        "sql": 'SELECT COUNT(*) FROM "orders" WHERE "created_at" >= \'2026-10-01\' AND "created_at" < \'2026-11-01\''
    },
    {
        "question": "Tìm các sản phẩm chưa bao giờ được bán",
        "sql": 'SELECT "product_id", "product_name" FROM "products" WHERE NOT EXISTS (SELECT 1 FROM "order_items" WHERE "order_items"."product_id" = "products"."product_id")'
    }
]

async def main():
    logger.info("Starting few-shot examples indexing into Qdrant...")
    
    qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model, 
        api_key=settings.openai_api_key
    )
    
    collections = qdrant.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        logger.info(f"Creating collection {COLLECTION_NAME}")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
    else:
        logger.info(f"Collection {COLLECTION_NAME} already exists. Recreating it.")
        qdrant.delete_collection(COLLECTION_NAME)
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )

    points = []
    
    for idx, example in enumerate(FEW_SHOT_EXAMPLES):
        question = example["question"]
        sql = example["sql"]
        
        vector = embeddings.embed_query(question)
        
        payload = {
            "question": question,
            "sql": sql
        }
        
        points.append(
            PointStruct(
                id=idx + 1,
                vector=vector,
                payload=payload
            )
        )
        logger.info(f"Generated embedding for: '{question}'")

    if points:
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        logger.info(f"Successfully inserted {len(points)} few-shot examples into Qdrant.")

if __name__ == "__main__":
    asyncio.run(main())
