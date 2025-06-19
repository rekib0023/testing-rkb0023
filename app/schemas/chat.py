from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    context: Optional[List[str]] = None


class Source(BaseModel):
    content: str
    metadata: Dict[str, Any]


class ChatResponse(BaseModel):
    response: str
    sources: List[Source]
    # confidence: float # Removed confidence score
