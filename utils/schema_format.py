"""
Render schema_context / business_context thành text cho prompt.

Trước đây hàm _format_schema_context bị copy nguyên xi ở sql_plan_agent và
sql_gen_agent. Sau khi gộp hai node, chỉ còn một nơi dùng — nhưng vẫn tách ra
đây để sql_gen_agent chỉ chứa logic của node.
"""
from __future__ import annotations

from config import get_settings
from graph.state import TableSchema

settings = get_settings()


def format_schema_context(schemas: list[TableSchema]) -> str:
    parts = []
    for s in schemas:
        col_lines = []
        for c in s["columns"]:
            null_str = " NULL" if c.get("nullable") else " NOT NULL"
            extra = []
            if c.get("comment"):
                extra.append(f"DB Comment: {c['comment']}")
            if c.get("excel_vi_name"):
                extra.append(f"Tên TV: {c['excel_vi_name']}")
            if c.get("excel_note"):
                extra.append(f"Ghi chú: {c['excel_note']}")
            extra_str = f"  -- {', '.join(extra)}" if extra else ""
            col_lines.append(f'    - "{c["name"]}" {c["type"].upper()}{null_str}{extra_str}')

        sample = ""
        if s.get("sample_rows"):
            sample = f"\n  Sample: {s['sample_rows'][0]}"

        fks_str = ""
        if s.get("foreign_keys"):
            fks = [
                f"    - {fk['column_name']} REFERENCES {fk['foreign_table']}({fk['foreign_column']})"
                for fk in s["foreign_keys"]
            ]
            fks_str = "\n  Foreign Keys:\n" + "\n".join(fks)

        desc_parts = []
        if s.get("description"):
            desc_parts.append(f"DB Desc: {s['description']}")
        if s.get("excel_table_desc"):
            desc_parts.append(f"Tên TV: {s['excel_table_desc']}")
        if s["table_name"] in settings.TABLE_RULES:
            desc_parts.append(f"Quy tắc (BẮT BUỘC): {settings.TABLE_RULES[s['table_name']]}")
        desc = f"\n  Description: ({' | '.join(desc_parts)})" if desc_parts else ""

        parts.append(f'Table: "{s["table_name"]}"{desc}\n{chr(10).join(col_lines)}{fks_str}{sample}')
    return "\n\n".join(parts)


def format_business_context(b_ctx: list[dict]) -> str:
    if not b_ctx:
        return "Không có quy định nghiệp vụ nào liên quan."
    return "\n".join(
        f"- Từ khóa: {c['tu_khoa']}\n  Định nghĩa (Logic): {c['dinh_nghia_sql_logic']}"
        for c in b_ctx
    )
