"""
Schema linking: tìm những bảng cần cho câu hỏi.

Retrieval hai tầng + từ vựng, rồi LLM chọn từ danh sách ứng viên có mô tả.

Vì sao không dùng ngưỡng cosine tuyệt đối: điểm cosine giữa câu hỏi ngắn và mô tả
bảng luôn quanh 0.4–0.6, ngưỡng cũ 0.68 chưa bao giờ có bảng nào vượt qua — vector
search là code chết và LLM fallback (253 tên bảng trần, trần "5 bảng") gánh hết.
Thứ hạng thì ổn định; điểm tuyệt đối thì không.

Điểm của một bảng = kết hợp:
  - cosine của chính bảng (text ngắn: tên + mô tả TV)
  - cosine tốt nhất trong các CỘT của bảng ("trạng thái học" kéo SinhVien lên qua trangThaiHoc)
  - khớp từ vựng: mô tả TV / tên bảng xuất hiện nguyên cụm trong câu hỏi
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from config import get_settings
from db.introspect import fetch_table_schema
from graph.state import AgentState, TableSchema
from prompts.schema_select import SCHEMA_SELECT_SYSTEM, SCHEMA_SELECT_HUMAN
from utils.llm import make_llm
from utils.text_norm import normalize, split_camel

logger = logging.getLogger(__name__)
settings = get_settings()

_llm = make_llm(temperature=0)

TABLE_TOP_K = 30          # số bảng lấy từ tầng bảng
COLUMN_TOP_K = 150        # số cột lấy từ tầng cột (nhiều bảng chia sẻ tên cột giống nhau)
CANDIDATES = 20           # số ứng viên đưa cho LLM
FALLBACK_PICK = 3         # nếu LLM lỗi: lấy top-N theo điểm kết hợp
_CATALOG_TTL = 600        # giây — cache danh sách bảng (tên, mô tả, số dòng) để quét từ vựng

W_TABLE, W_COLUMN, W_LEXICAL, W_PRIOR = 0.40, 0.30, 0.20, 0.10

# Từ chung chung trong mô tả bảng, không mang thông tin khi so khớp từng từ.
_STOPWORDS = {"thong", "tin", "danh", "muc", "bang", "du", "lieu", "cua", "va", "theo", "cac", "dm"}


@lru_cache(maxsize=1)
def _qdrant() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


@lru_cache(maxsize=1)
def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)


@dataclass
class Candidate:
    table: str
    desc: str = ""
    row_count: int = 0
    fk_tables: list[str] = field(default_factory=list)
    schema_json: str = ""
    table_score: float = 0.0
    column_score: float = 0.0
    lexical: float = 0.0
    matched_columns: list[str] = field(default_factory=list)

    @property
    def prior(self) -> float:
        # Bảng lớn thường là bảng thực thể / bảng sự kiện chính; bảng 0 dòng không trả lời được gì.
        return min(math.log10(self.row_count + 1) / 6.0, 1.0)

    @property
    def score(self) -> float:
        return (W_TABLE * self.table_score + W_COLUMN * self.column_score
                + W_LEXICAL * self.lexical + W_PRIOR * self.prior)


class TableSelection(BaseModel):
    tables: list[str] = Field(description="Tên các bảng cần thiết, viết đúng y nguyên.")


def _lexical_score(query_norm: str, table: str, desc: str) -> float:
    """
    1.0  mô tả TV xuất hiện nguyên cụm trong câu hỏi ("Ngành" trong "bao nhiêu ngành đào tạo")
    0.8  tên bảng (tách camelCase) xuất hiện nguyên cụm
    else tỉ lệ từ của mô tả có mặt trong câu hỏi (bỏ stopword) — chỉ là tie-breaker
    """
    d = normalize(desc)
    if d and len(d) >= 3 and f" {d} " in f" {query_norm} ":
        return 1.0
    t = split_camel(table)
    if t and f" {t} " in f" {query_norm} ":
        return 0.8
    tokens = [w for w in d.split() if w not in _STOPWORDS]
    if not tokens:
        return 0.0
    q = set(query_norm.split())
    return sum(1 for w in tokens if w in q) / len(tokens) * 0.6


_catalog_cache: dict[str, tuple[float, list[dict]]] = {}


async def _catalog(domain: str) -> list[dict]:
    """Payload gọn của MỌI bảng trong domain (không vector), cache theo TTL — để quét từ vựng."""
    import time
    now = time.monotonic()
    cached = _catalog_cache.get(domain)
    if cached and now - cached[0] < _CATALOG_TTL:
        return cached[1]
    rows: list[dict] = []
    offset = None
    while True:
        pts, offset = await _qdrant().scroll(
            f"schema_collection_{domain}", limit=256, offset=offset, with_payload=True, with_vectors=False,
        )
        rows.extend(p.payload for p in pts if p.payload)
        if offset is None:
            break
    _catalog_cache[domain] = (now, rows)
    return rows


async def _retrieve_candidates(domain: str, user_query: str) -> list[Candidate]:
    qdrant = _qdrant()
    vector = await _embeddings().aembed_query(user_query)
    table_res, column_res = await asyncio.gather(
        qdrant.query_points(f"schema_collection_{domain}", query=vector, limit=TABLE_TOP_K, with_payload=True),
        qdrant.query_points(f"schema_columns_{domain}", query=vector, limit=COLUMN_TOP_K, with_payload=True),
    )

    cands: dict[str, Candidate] = {}

    def get(table: str) -> Candidate:
        if table not in cands:
            cands[table] = Candidate(table=table)
        return cands[table]

    for hit in table_res.points:
        p = hit.payload or {}
        c = get(p["table_name"])
        c.table_score = max(c.table_score, hit.score)
        c.desc, c.row_count = p.get("table_desc", ""), p.get("row_count", 0)
        c.fk_tables, c.schema_json = p.get("fk_tables", []), p.get("schema_json", "")

    for hit in column_res.points:
        p = hit.payload or {}
        c = get(p["table_name"])
        if hit.score > c.column_score:
            c.column_score = hit.score
        if len(c.matched_columns) < 3:
            label = p.get("vi_name") or p["column_name"]
            c.matched_columns.append(f"{label} ({p['column_name']})")

    # Bảng chỉ xuất hiện ở tầng cột chưa có payload — nạp bổ sung.
    missing = [t for t, c in cands.items() if not c.schema_json]
    if missing:
        pts, _ = await qdrant.scroll(
            f"schema_collection_{domain}", limit=len(missing), with_payload=True, with_vectors=False,
            scroll_filter=Filter(should=[FieldCondition(key="table_name", match=MatchValue(value=t)) for t in missing]),
        )
        for pt in pts:
            p = pt.payload or {}
            c = cands[p["table_name"]]
            c.desc, c.row_count = p.get("table_desc", ""), p.get("row_count", 0)
            c.fk_tables, c.schema_json = p.get("fk_tables", []), p.get("schema_json", "")

    # Quét từ vựng trên TOÀN BỘ bảng: bảng có mô tả / tên khớp nguyên cụm luôn được vào
    # danh sách, kể cả khi vector xếp nó ngoài top-K ("Nganh" từng đứng hạng 26/253 cho
    # câu "bao nhiêu ngành đào tạo" vì mọi bảng *DaoTao khác đều khớp "đào tạo").
    query_norm = normalize(user_query)
    for p in await _catalog(domain):
        lex = _lexical_score(query_norm, p["table_name"], p.get("table_desc", ""))
        if lex >= 0.8 and p["table_name"] not in cands:
            c = get(p["table_name"])
            c.desc, c.row_count = p.get("table_desc", ""), p.get("row_count", 0)
            c.fk_tables, c.schema_json = p.get("fk_tables", []), p.get("schema_json", "")
    for c in cands.values():
        c.lexical = _lexical_score(query_norm, c.table, c.desc)

    ranked = sorted(cands.values(), key=lambda c: c.score, reverse=True)[:CANDIDATES]

    # Bảng có quy tắc nghiệp vụ (TABLE_RULES) là bảng trọng yếu — luôn cho LLM thấy, kèm quy tắc,
    # để câu hỏi mơ hồ ("tín chỉ tích luỹ", "lượt học") có cơ hội chọn đúng dù vector xếp thấp.
    present = {c.table for c in ranked}
    for p in await _catalog(domain):
        t = p["table_name"]
        if t in settings.TABLE_RULES and t not in present:
            c = cands.get(t) or Candidate(table=t)
            c.desc, c.row_count = p.get("table_desc", ""), p.get("row_count", 0)
            c.fk_tables, c.schema_json = p.get("fk_tables", []), p.get("schema_json", "")
            ranked.append(c)
    logger.info("[SchemaAgent] ứng viên: %s",
                ", ".join(f"{c.table}={c.score:.2f}(t{c.table_score:.2f}/c{c.column_score:.2f}/l{c.lexical:.1f}/p{c.prior:.1f})" for c in ranked))
    return ranked


def _format_candidates(cands: list[Candidate]) -> str:
    lines = []
    for c in cands:
        parts = [f"- {c.table}"]
        if c.desc:
            parts.append(f"— {c.desc}")
        parts.append(f"({c.row_count:,} dòng)".replace(",", "."))
        if c.matched_columns:
            parts.append("| cột khớp: " + ", ".join(c.matched_columns))
        if c.fk_tables:
            parts.append("| liên kết: " + ", ".join(c.fk_tables[:8]))
        lines.append(" ".join(parts))
    return "\n".join(lines)


async def _select_tables(user_query: str, cands: list[Candidate]) -> list[str]:
    rules = "\n".join(f"- {k}: {v}" for k, v in settings.TABLE_RULES.items())
    messages = [
        SystemMessage(content=SCHEMA_SELECT_SYSTEM),
        HumanMessage(content=SCHEMA_SELECT_HUMAN.format(
            user_query=user_query, candidates=_format_candidates(cands), rules=rules,
        )),
    ]
    try:
        result = await _llm.with_structured_output(TableSelection).ainvoke(messages)
        picked = [t.strip() for t in result.tables if t.strip()]
    except Exception as exc:
        logger.error("[SchemaAgent] LLM chọn bảng lỗi: %s", exc)
        picked = []

    allowed = {c.table for c in cands} | {t for c in cands for t in c.fk_tables}
    valid = [t for t in picked if t in allowed]
    dropped = set(picked) - set(valid)
    if dropped:
        logger.warning("[SchemaAgent] LLM trả bảng ngoài danh sách, bỏ: %s", dropped)
    if not valid:
        valid = [c.table for c in cands[:FALLBACK_PICK]]
        logger.warning("[SchemaAgent] không có lựa chọn hợp lệ — dùng top-%d: %s", FALLBACK_PICK, valid)
    return valid


async def _load_schemas(domain: str, tables: list[str], cands: list[Candidate]) -> list[TableSchema]:
    """schema_json trong payload đã gồm tên TV + FK Excel; bảng ngoài ứng viên thì tra Qdrant, cuối cùng mới hỏi DB."""
    by_name = {c.table: c for c in cands}
    out: list[TableSchema] = []
    for t in tables:
        c = by_name.get(t)
        if c and c.schema_json:
            out.append(json.loads(c.schema_json))
            continue
        pts, _ = await _qdrant().scroll(
            f"schema_collection_{domain}", limit=1, with_payload=True, with_vectors=False,
            scroll_filter=Filter(must=[FieldCondition(key="table_name", match=MatchValue(value=t))]),
        )
        if pts and pts[0].payload.get("schema_json"):
            out.append(json.loads(pts[0].payload["schema_json"]))
        else:
            try:
                out.append(await fetch_table_schema(domain, t))
            except Exception as exc:
                logger.error("[SchemaAgent] không lấy được schema %s: %s", t, exc)
    return out


async def schema_agent(state: AgentState) -> dict:
    """
    Đọc : user_query, domain, selected_tables
    Ghi  : relevant_tables, schema_context
    """
    domain = state.get("domain", "qldt")
    user_query = state["user_query"]

    selected = state.get("selected_tables")
    if selected:
        logger.info("[SchemaAgent] giới hạn theo bảng người dùng chọn: %s", selected)
        schemas = await _load_schemas(domain, selected, [])
        return {"relevant_tables": [s["table_name"] for s in schemas], "schema_context": schemas}

    try:
        cands = await _retrieve_candidates(domain, user_query)
    except Exception as exc:
        logger.error("[SchemaAgent] retrieval lỗi (Qdrant chưa index?): %s", exc, exc_info=True)
        return {"relevant_tables": [], "schema_context": []}
    if not cands:
        return {"relevant_tables": [], "schema_context": []}

    tables = await _select_tables(user_query, cands)
    schemas = await _load_schemas(domain, tables, cands)
    logger.info("[SchemaAgent] chọn: %s", tables)
    return {"relevant_tables": tables, "schema_context": schemas}
