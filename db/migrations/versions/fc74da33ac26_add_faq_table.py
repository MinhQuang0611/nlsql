"""Add FAQ table

Revision ID: fc74da33ac26
Revises: e1edb74afe77
Create Date: 2026-04-02 16:48:43.537081

Sửa ngày 2026-09-25: bản autogenerate cũ không tạo bảng FAQ mà DROP conversations, messages, checkpoint_*
(các bảng do create_all và LangGraph quản lý, không thuộc alembic). Chạy bản cũ sẽ mất lịch sử chat.
Bảng có thể đã được tạo bằng Base.metadata.create_all, nên upgrade bỏ qua nếu bảng đã có.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fc74da33ac26"
down_revision: Union[str, None] = 'e1edb74afe77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("FAQ"):
        return
    op.create_table(
        "FAQ",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cau_hoi", sa.String(500), nullable=False),
        sa.Column("cau_tra_loi", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_FAQ_cau_hoi", "FAQ", ["cau_hoi"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_FAQ_cau_hoi", table_name="FAQ")
    op.drop_table("FAQ")
