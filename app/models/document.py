from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class Document(BaseModel):
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[list[float]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True
