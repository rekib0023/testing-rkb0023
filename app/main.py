from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pathlib import Path
from app.api.api import api_router
from app.api.chat import router as chat_router
from app.api.monitoring import router as monitoring_router
from app.config.config import settings
import time

app = FastAPI(
    title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(chat_router, prefix=settings.API_V1_STR)
app.include_router(monitoring_router, prefix=settings.API_V1_STR)


@app.get("/", response_class=HTMLResponse)
def root():
    return "<html><body><h1>Legal AI API</h1><p>API is running. See /docs for API documentation.</p></body></html>"

@app.get("/health", response_class=JSONResponse)
def health_check():
    """Health check endpoint to verify the API is running properly."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.VERSION
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
