"""Add app_user table (tài khoản quản trị semantic layer)

Revision ID: a3c9e5f1d2b7
Revises: fc74da33ac26
Create Date: 2026-09-25

Revision trước (fc74da33ac26) đã được sửa ngày 2026-09-25; trước đó nó DROP bảng chat.

Bảng này có thể đã được scripts/create_users.py tạo sẵn (checkfirst), nên upgrade
bỏ qua nếu bảng đã có.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3c9e5f1d2b7"
down_revision: Union[str, None] = "fc74da33ac26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("app_user"):
        return
    op.create_table(
        "app_user",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("role IN ('editor', 'approver', 'admin')", name="ck_app_user_role"),
    )
    op.create_index("ix_app_user_username", "app_user", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_app_user_username", table_name="app_user")
    op.drop_table("app_user")
