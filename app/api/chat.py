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
    # The chat_service now handles exceptions internally and returns a valid ChatResponse
    # We can directly return the result from the service
    logger.info(f"Received chat request: {request.message[:100]}...")
    response_object = await chat_service.get_response(request.message, request.context)
    # Check if the response indicates an internal error from the service
    if response_object.confidence == 0.0 and response_object.response.startswith("Error:"):
         logger.error(f"Chat service returned an error: {response_object.response}")
         # Optionally, still raise HTTPException for client awareness, but use the service's error message
         # raise HTTPException(status_code=500, detail=response_object.response)
         # Or just return the error response object directly:
         return response_object
    else:
        logger.info("Successfully processed chat request")
        return response_object
