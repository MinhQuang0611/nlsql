"""Khoi tao bang QuyDinhNghiepVu

Revision ID: e1edb74afe77
Revises: 
Create Date: 2026-04-02 07:18:39.186675

Sửa ngày 2026-09-25: bản autogenerate cũ rỗng (pass), không tạo bảng nào.
Bảng có thể đã được tạo bằng Base.metadata.create_all, nên upgrade bỏ qua nếu bảng đã có.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1edb74afe77"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("QuyDinhNghiepVu"):
        return
    op.create_table(
        "QuyDinhNghiepVu",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tu_khoa", sa.String(255), nullable=False),
        sa.Column("dinh_nghia_sql_logic", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_QuyDinhNghiepVu_tu_khoa", "QuyDinhNghiepVu", ["tu_khoa"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_QuyDinhNghiepVu_tu_khoa", table_name="QuyDinhNghiepVu")
    op.drop_table("QuyDinhNghiepVu")
