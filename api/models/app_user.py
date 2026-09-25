"""
Tài khoản quản trị của nlsql: người soạn, người duyệt định nghĩa semantic layer, và admin.

Vai trò (xem docs/plan_semantic_layer.md §6.1):
- editor   : soạn, sửa bản nháp, gửi duyệt
- approver : duyệt / từ chối, xuất bản release
- admin    : mọi quyền của approver + quản lý tài khoản, quay lại release cũ
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, String

from db.connection import Base

ROLES = ("editor", "approver", "admin")


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint(f"role IN {ROLES}", name="ck_app_user_role"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(64), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    # Tài khoản tạo sẵn phải đổi mật khẩu ở lần đăng nhập đầu tiên.
    must_change_password = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
