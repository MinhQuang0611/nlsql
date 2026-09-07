from sqlalchemy import Column , String , Integer , ForeignKey , DateTime , Boolean
from sqlalchemy.orm import relationship 
from sqlalchemy.types import JSON
from app.models.model_base import BareBaseModel

class LongTermMemory(BareBaseModel):
    __tablename__ = "long_term_memory"
    
    user_id = Column(Integer, nullable=False)
    name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    language = Column(String, nullable=True) 
    
    