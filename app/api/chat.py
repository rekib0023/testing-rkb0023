from fastapi import APIRouter, Depends

from app.core.dependencies import get_chat_service
from app.core.logging_config import get_logger
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

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
    # The service now handles errors internally and returns a valid ChatResponse
    response_object = await chat_service.get_response(request.message, request.context)

    # Log if the service returned an error message within the response
    if response_object.response.startswith("Error:"):
        logger.error(
            f"Chat service processing resulted in an error: {response_object.response}"
        )
        # We still return the response object as it conforms to the schema
    else:
        logger.info("Successfully processed chat request")

    return response_object
