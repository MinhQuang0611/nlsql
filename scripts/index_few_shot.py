"""
Index few-shot (câu hỏi -> SQL) vào Qdrant, TÁCH RIÊNG THEO DOMAIN.

Hai thay đổi so với bản cũ:

1. Collection cũ dùng chung một tên `few_shot_collection` cho mọi domain, nên ví dụ
   SQL của qldt bị nhét vào prompt sinh SQL cho tcns. Nay mỗi domain có collection
   riêng: `few_shot_collection_<domain>`.

2. Dữ liệu seed cũ là ví dụ e-commerce (orders / products / customers) — không có
   bảng nào trong số đó tồn tại trong DB này, nên few-shot chỉ làm nhiễu prompt.
   Nay ví dụ nạp từ `config/few_shot_<domain>.json` và ĐƯỢC KIỂM CHỨNG bằng EXPLAIN
   trên chính DB của domain trước khi index — ví dụ sai cú pháp hoặc sai tên cột
   bị loại, không lọt vào prompt.

Chạy:  python -m scripts.index_few_shot           # tất cả domain
       python -m scripts.index_few_shot qldt      # một domain
"""
import asyncio
import json
import logging
import sys
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from langchain_openai import OpenAIEmbeddings

from config import get_settings
from db.connection import is_clickhouse, ch_execute, get_db_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def collection_name(domain: str) -> str:
    return f"few_shot_collection_{domain}"


def load_examples(domain: str) -> list[dict]:
    path = CONFIG_DIR / f"few_shot_{domain}.json"
    if not path.exists():
        logger.warning("Không có file few-shot cho domain '%s' (%s)", domain, path)
        return []
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    logger.info("Đọc %d ví dụ từ %s", len(data), path.name)
    return data


async def _validate_sql(domain: str, sql: str) -> str | None:
    """
    Kiểm chứng một ví dụ few-shot. Trả về None nếu hợp lệ, ngược lại là lý do loại.

    CHẠY THẬT chứ không chỉ EXPLAIN. Lý do: EXPLAIN chỉ bắt lỗi cú pháp và tên cột.
    Một ví dụ như `WHERE trangThaiHoc = 'DANG_HOC'` qua EXPLAIN trót lọt nhưng trả về
    0 dòng vì giá trị thật trong DB là 'Đang học'. Ví dụ kiểu đó nếu lọt vào prompt sẽ
    dạy LLM viết sai giá trị enum cho MỌI câu hỏi sau đó — tác hại lớn hơn là không có
    few-shot nào.
    """
    try:
        if is_clickhouse(domain):
            rows = await ch_execute(domain, sql)
        else:
            from sqlalchemy import text
            async with get_db_context(domain) as db:
                result = await db.execute(text(sql))
                rows = result.fetchall()
    except Exception as exc:
        return str(exc).split("\n")[0][:300]

    if not rows:
        return (
            "chạy được nhưng trả về 0 dòng — nhiều khả năng sai giá trị enum "
            "trong WHERE hoặc sai khoá JOIN"
        )
    return None


async def index_domain(domain: str, qdrant: QdrantClient, embeddings: OpenAIEmbeddings) -> int:
    examples = load_examples(domain)
    if not examples:
        return 0

    # 1. Kiểm chứng từng ví dụ trên DB thật trước khi tốn tiền embedding.
    valid: list[dict] = []
    for ex in examples:
        err = await _validate_sql(domain, ex["sql"])
        if err:
            logger.error("  [LOẠI] %r\n         lý do: %s", ex["question"], err)
        else:
            valid.append(ex)
            logger.info("  [OK]   %r", ex["question"])

    if not valid:
        logger.error("Domain '%s': không ví dụ nào hợp lệ — bỏ qua indexing.", domain)
        return 0

    logger.info("Domain '%s': %d/%d ví dụ hợp lệ.", domain, len(valid), len(examples))

    # 2. Tạo lại collection.
    name = collection_name(domain)
    existing = {c.name for c in qdrant.get_collections().collections}
    if name in existing:
        qdrant.delete_collection(name)
    qdrant.create_collection(
        collection_name=name,
        vectors_config=VectorParams(
            size=settings.embedding_dimensions, distance=Distance.COSINE
        ),
    )

    # 3. Embed + upsert.
    points = [
        PointStruct(
            id=idx + 1,
            vector=embeddings.embed_query(ex["question"]),
            payload={"question": ex["question"], "sql": ex["sql"], "domain": domain},
        )
        for idx, ex in enumerate(valid)
    ]
    qdrant.upsert(collection_name=name, points=points)
    logger.info("Đã nạp %d ví dụ vào '%s'.", len(points), name)
    return len(points)


async def main(domains: list[str] | None = None) -> None:
    domains = domains or settings.list_domains()
    qdrant = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model, api_key=settings.openai_api_key
    )

    total = 0
    for domain in domains:
        logger.info("--- Domain: %s ---", domain)
        try:
            total += await index_domain(domain, qdrant, embeddings)
        except Exception as exc:
            logger.error("Domain '%s' lỗi: %s", domain, exc)
    logger.info("Xong. Tổng %d ví dụ được index.", total)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or None))
