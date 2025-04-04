from fastapi import APIRouter, Depends
from app.core.monitoring import MonitoringService
from app.core.dependencies import get_document_service, get_chat_service
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService
from app.config.config import settings

router = APIRouter(prefix=settings.API_V1_STR)


@router.get("/health")
async def health_check(
    document_service: DocumentService = Depends(get_document_service),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Check the health of the application and its services"""
    return {
        "status": "healthy",
        "services": {"document_service": "running", "chat_service": "running"},
    }


@router.get("/metrics")
async def get_metrics(
    document_service: DocumentService = Depends(get_document_service),
    chat_service: ChatService = Depends(get_chat_service),
):
    """Get application metrics"""
    return {
        "document_service": document_service.monitoring.get_metrics(),
        "chat_service": chat_service.monitoring.get_metrics(),
    }
