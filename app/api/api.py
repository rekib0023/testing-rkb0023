from fastapi import APIRouter

from app.config.config import settings

api_router = APIRouter()


@api_router.get("/")
async def root():
    return {
        "message": "Welcome to Legal AI Assistant API",
        "version": "1.0.0",
        "docs_url": f"{settings.API_V1_STR}/docs",
    }
