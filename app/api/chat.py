from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from app.services.chat_service import ChatService
from app.core.dependencies import get_chat_service
from app.core.logging_config import get_logger
from app.schemas.chat import ChatRequest, ChatResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest, chat_service: ChatService = Depends(get_chat_service)
):
    """Process a chat message and return a response"""
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")
        response = await chat_service.get_response(request.message, request.context)
        logger.info("Successfully processed chat request")
        return response
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing chat request: {str(e)}"
        )
