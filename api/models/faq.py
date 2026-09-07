from sqlalchemy import Column, String, Text, DateTime
import uuid
from datetime import datetime
from db.connection import Base

class FAQ(Base):
    __tablename__ = "FAQ"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cau_hoi = Column(String(500), nullable=False, unique=True, index=True)
    cau_tra_loi = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
