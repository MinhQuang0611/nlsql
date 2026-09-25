from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class FAQCreate(BaseModel):
    cau_hoi: str = Field(..., max_length=500, description="Câu hỏi thường gặp")
    cau_tra_loi: str = Field(..., description="Câu trả lời tương ứng")

class FAQUpdate(BaseModel):
    cau_hoi: Optional[str] = Field(None, max_length=500)
    cau_tra_loi: Optional[str] = None

class FAQResponse(BaseModel):
    id: str
    cau_hoi: str
    cau_tra_loi: str
    updated_at: datetime

    class Config:
        from_attributes = True
