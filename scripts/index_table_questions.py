import asyncio
import json
import logging
import uuid
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config import get_settings
from agents.schema_agent import _fetch_all_tables, _fetch_table_schema
from scripts.index_schema import load_excel_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

COLLECTION_NAME = "table_questions_collection"

class GeneratedQuestions(BaseModel):
    questions: list[str] = Field(description="Danh sách các câu hỏi tiếng Việt")

async def generate_questions_for_table(llm: ChatOpenAI, table_name: str, schema_context: str) -> List[str]:
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Bạn là một chuyên gia phân tích dữ liệu và hiểu rõ cách người dùng thường đặt câu hỏi truy vấn cơ sở dữ liệu. Nhiệm vụ của bạn là sinh ra các câu hỏi tự nhiên bằng tiếng Việt."),
        ("user", "Dựa vào thông tin cấu trúc của bảng '{table_name}' dưới đây:\n\n{schema_context}\n\n"
                 "Hãy tạo từ 10 đến 20 câu hỏi bằng tiếng Việt mà người dùng có thể hỏi (mang tính thực tế) liên quan đến dữ liệu trong bảng này. "
                 "Hãy trả về dưới dạng JSON danh sách các câu hỏi thông qua format bạn được cấp.")
    ])
    
    structured_llm = llm.with_structured_output(GeneratedQuestions)
    chain = prompt | structured_llm
    
    try:
        result = await chain.ainvoke({"table_name": table_name, "schema_context": schema_context})
        return result.questions
    except Exception as e:
        logger.error(f"Error generating questions for table {table_name}: {e}")
        return []

async def main():
    logger.info("Starting table questions generation and indexing into Qdrant...")
    
    qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model, 
        api_key=settings.openai_api_key
    )
    
    llm = ChatOpenAI(
        model=settings.openai_model, # Sử dụng model mặc định (ví dụ: gpt-4o-mini)
        api_key=settings.openai_api_key,
        temperature=0.7
    )
    
    collections = qdrant.get_collections().collections
    if not any(c.name == COLLECTION_NAME for c in collections):
        logger.info(f"Creating collection {COLLECTION_NAME}")
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
    else:
        logger.info(f"Collection {COLLECTION_NAME} already exists. We will continue and append to it.")

    all_tables = await _fetch_all_tables()
    logger.info(f"Found {len(all_tables)} tables in database.")
    
    excel_metadata = load_excel_metadata("QLDT_FINAL.xlsx")
    
    all_points = []
    
    for table_name in all_tables:
        schema = await _fetch_table_schema(table_name)
        
        table_meta = excel_metadata.get(table_name, {})
        excel_table_desc = table_meta.get("table_desc", "")
        col_meta_dict = table_meta.get("columns", {})
        
        col_vi_parts = []
        for c in schema["columns"]:
            c_name = c["name"]
            c_meta = col_meta_dict.get(c_name, {})
            vi_name = c_meta.get("vi_name", "")
            note = c_meta.get("note", "")
            
            label = f"{c_name}"
            if vi_name:
                label += f" ({vi_name})"
            if note:
                label += f" - {note}"
            col_vi_parts.append(label)
            
        columns_str = "\n".join(f" - {part}" for part in col_vi_parts)
        
        table_desc_str = f"Mô tả bảng: {excel_table_desc}\n" if excel_table_desc else ""
        schema_context = f"{table_desc_str}Các cột trong bảng:\n{columns_str}"
        
        logger.info(f"Generating questions for table {table_name}...")
        questions = await generate_questions_for_table(llm, table_name, schema_context)
        
        if not questions:
            continue
            
        logger.info(f"Generated {len(questions)} questions for {table_name}.")
        
        # Nhúng hàng loạt (batch embedding) để tối ưu
        question_embeddings = await embeddings.aembed_documents(questions)
        
        for q_text, q_vec in zip(questions, question_embeddings):
            payload = {
                "table_name": table_name,
                "question": q_text,
                "type": "generated_table_question"
            }
            point_id = str(uuid.uuid4())
            
            all_points.append(
                PointStruct(
                    id=point_id,
                    vector=q_vec,
                    payload=payload
                )
            )

    if all_points:
        # Chia batch upload lên Qdrant để tránh lỗi khi payload quá lớn
        batch_size = 100
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i+batch_size]
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
        logger.info(f"Successfully inserted {len(all_points)} questions into Qdrant collection {COLLECTION_NAME}.")
    else:
        logger.warning("No questions were generated or indexed.")

if __name__ == "__main__":
    asyncio.run(main())
