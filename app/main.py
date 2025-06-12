from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.monitoring import router as monitoring_router
from app.config.config import settings

# ## --- IMPROVEMENT ---: Import the services to be managed.
from app.services.chat_service import ChatService
from app.services.document_service import DocumentService
from app.services.monitoring_service import MonitoringService


# ## --- CRITICAL FIX ---: Implement the application lifespan manager.
# This ensures services are initialized at startup and cleaned up at shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the application's startup and shutdown events.
    """
    # --- Startup ---
    # Create singleton instances of services
    app.state.document_service = DocumentService()
    app.state.monitoring_service = MonitoringService()
    app.state.chat_service = ChatService()

    # Initialize services
    await app.state.document_service.initialize()
    await app.state.monitoring_service.initialize()
    await app.state.chat_service.initialize()

    print("--- Services Initialized ---")
    yield
    # --- Shutdown ---
    await app.state.document_service.cleanup()
    await app.state.monitoring_service.cleanup()
    await app.state.chat_service.cleanup()
    print("--- Services Cleaned Up ---")


# Initialize the FastAPI app with the lifespan manager and metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# ## --- IMPROVEMENT ---: Use settings for CORS origins for security.
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files for serving the frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# ## --- IMPROVEMENT ---: Centralized API router for better organization.
# This main router will include all other API routers.
api_router = APIRouter()
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["Monitoring"])

app.include_router(api_router, prefix=settings.API_V1_STR)


# ## --- IMPROVEMENT ---: Add a health check endpoint.
# This is a standard practice for confirming the API is running.
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    """Serves the main index.html file."""
    return FileResponse("app/static/index.html")


if __name__ == "__main__":
    import uvicorn

    # ## --- IMPROVEMENT ---: Run configuration pulled from settings.
    uvicorn.run(
        "app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True
    )
