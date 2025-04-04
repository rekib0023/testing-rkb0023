from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class ChatRequest(BaseModel):
    message: str
    context: Optional[List[str]] = None


class Source(BaseModel):
    content: str
    metadata: Dict[str, Any]


class ChatResponse(BaseModel):
    response: str
    sources: List[Source]
    confidence: float
