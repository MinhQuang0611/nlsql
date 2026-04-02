from sqlalchemy import Column, Text, Enum, ForeignKey, JSON, Integer
from sqlalchemy.orm import relationship
from app.models.model_base import BareBaseModel
from app.utils.enums import SenderType

class Message(BareBaseModel):
    __tablename__ = "message"

    sender = Column(Enum(SenderType), nullable=False)
    content = Column(Text, nullable=True)
    meta_info = Column(JSON, nullable=True)

    longterm_id = Column(Integer, ForeignKey("long_term_memory.id"), nullable=False)

    longterm = relationship("LongTermMemory", back_populates="messages")
