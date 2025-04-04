from fastapi import Depends
from app.services.document_service import DocumentService
from app.services.chat_service import ChatService

_document_service = None
_chat_service = None


async def get_document_service() -> DocumentService:
    """Dependency for DocumentService"""
    global _document_service
    if _document_service is None:
        _document_service = DocumentService()
        await _document_service.initialize()
    return _document_service


async def get_chat_service() -> ChatService:
    """Dependency for ChatService"""
    global _chat_service
    if _chat_service is None:
        document_service = await get_document_service()
        _chat_service = ChatService()
        _chat_service.document_service = document_service
        await _chat_service.initialize()
    return _chat_service
