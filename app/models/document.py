from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class Document(BaseModel):
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[list[float]] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True
