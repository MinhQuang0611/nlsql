import asyncio
import json
import logging
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings
import pandas as pd

from config import get_settings
from db.connection import get_db_context
from agents.schema_agent import _fetch_all_tables, _fetch_table_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

COLLECTION_NAME = "schema_collection"

def load_excel_metadata(file_path: str) -> dict:
    """Read QLDT_FINAL.xlsx 'Database Schema' sheet and build a mapping dictionary."""
    mapping = {}
    try:
        df = pd.read_excel(file_path, sheet_name="Database Schema")
        df = df.fillna("")
        current_table = None
        
        for _, row in df.iterrows():
            thuoc_tinh = str(row.get("Tên thuộc tính", "")).strip()
            ten_bang = str(row.get("Tên bảng", "")).strip()
            tieng_viet = str(row.get("Tên tiếng Việt", "")).strip()
            ghi_chu = str(row.get("Ghi chú tham chiếu", "")).strip()
            
            if thuoc_tinh == "--- BẢNG ---" and ten_bang:
                current_table = ten_bang
                mapping[current_table] = {"table_desc": tieng_viet, "columns": {}}
            elif current_table and thuoc_tinh and thuoc_tinh != "--- BẢNG ---":
                mapping[current_table]["columns"][thuoc_tinh] = {
                    "vi_name": tieng_viet,
                    "note": ghi_chu
                }
        logger.info(f"Loaded Excel metadata for {len(mapping)} tables.")
    except Exception as e:
        logger.error(f"Failed to load Excel metadata: {e}")
    return mapping

async def main():
    logger.info("Starting schema indexing into Qdrant...")
    
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
        logger.info(f"Collection {COLLECTION_NAME} already exists. Skipping indexing.")
        return

    all_tables = await _fetch_all_tables()
    logger.info(f"Found {len(all_tables)} tables in database.")
    
    excel_metadata = load_excel_metadata("QLDT_FINAL.xlsx")
    
    points = []
    
    for idx, table_name in enumerate(all_tables):
        schema = await _fetch_table_schema(table_name)
        
        table_meta = excel_metadata.get(table_name, {})
        excel_table_desc = table_meta.get("table_desc", "")
        col_meta_dict = table_meta.get("columns", {})
        
        col_vi_parts = []
        enum_hints = []

        for c in schema["columns"]:
            c_name = c["name"]
            c_meta = col_meta_dict.get(c_name, {})
            vi_name = c_meta.get("vi_name", "")
            note = c_meta.get("note", "")
            db_comment = c.get("comment") or ""

            if vi_name or note:
                c["excel_vi_name"] = vi_name
                c["excel_note"] = note

            label = f"{vi_name} ({c_name})" if vi_name else c_name
            col_vi_parts.append(label)

            raw_note = note or db_comment
            if raw_note and "/" in raw_note:
                enum_hints.append(f"  - {label} có thể nhận giá trị: {raw_note}")

        if excel_table_desc:
            schema["excel_table_desc"] = excel_table_desc

        # Sentence 1: table purpose
        table_label = excel_table_desc if excel_table_desc else table_name
        db_desc = schema.get("description", "") or ""
        if db_desc and db_desc != excel_table_desc:
            sent1 = f"Bảng {table_name} lưu thông tin về {table_label}. {db_desc}"
        else:
            sent1 = f"Bảng {table_name} lưu thông tin về {table_label}."

        # Sentence 2: column list
        cols_str = ", ".join(col_vi_parts)
        sent2 = f"Các thông tin bao gồm: {cols_str}."

        # Sentence 3 (optional): enum/status hints
        sent3 = ""
        if enum_hints:
            sent3 = "\n" + "\n".join(enum_hints)

        # Sentence 4 (optional): foreign keys
        fks_str = ""
        if schema.get("foreign_keys"):
            fks = [
                f"  - {fk['column_name']} liên kết tới bảng {fk['foreign_table']}({fk['foreign_column']})"
                for fk in schema["foreign_keys"]
                if fk.get("column_name")
            ]
            if fks:
                fks_str = "\nLiên kết:\n" + "\n".join(fks)

        embed_text = f"{sent1}\n{sent2}{sent3}{fks_str}"
        
        vector = embeddings.embed_query(embed_text)
        
        payload = {
            "table_name": table_name,
            # "schema_json": json.dumps(schema, default=str),
            "embed_text": embed_text
        }
        
        points.append(
            PointStruct(
                id=idx + 1,
                vector=vector,
                payload=payload
            )
        )
        logger.info(f"Generated embedding for table: {table_name}")

    if points:
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )
        logger.info(f"Successfully inserted {len(points)} tables into Qdrant.")
    else:
        logger.warning("No tables were found to index.")

if __name__ == "__main__":
    asyncio.run(main())
