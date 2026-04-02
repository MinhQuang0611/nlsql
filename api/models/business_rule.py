from sqlalchemy import Column, String, Text, DateTime
import uuid
from datetime import datetime
from db.connection import Base

class BusinessRule(Base):
    __tablename__ = "QuyDinhNghiepVu"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tu_khoa = Column(String(255), nullable=False, unique=True, index=True)
    dinh_nghia_sql_logic = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
