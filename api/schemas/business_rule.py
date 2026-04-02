from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class BusinessRuleBase(BaseModel):
    tu_khoa: str
    dinh_nghia_sql_logic: str

class BusinessRuleCreate(BusinessRuleBase):
    pass

class BusinessRuleUpdate(BaseModel):
    tu_khoa: Optional[str] = None
    dinh_nghia_sql_logic: Optional[str] = None

class BusinessRuleResponse(BusinessRuleBase):
    id: str
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
