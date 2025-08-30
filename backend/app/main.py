from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from pathlib import Path
import logging
import os
from datetime import datetime
import uvicorn

from .config import settings
from .models import ServiceResponse, VideoUpload
from .database import get_supabase
from .routes import videos, events, organizations, ml_processing

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.RAILWAY_ENVIRONMENT}")
    
    # Download hockey model if not present
    try:
        import subprocess
        model_path = Path("models/hockey_yolo.pt")
        if not model_path.exists():
            logger.info("Hockey model not found, attempting to download...")
            result = subprocess.run(
                ["python", "scripts/setup_hockey_model.py"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.info("Hockey model downloaded successfully")
            else:
                logger.warning(f"Could not download hockey model: {result.stderr}")
        else:
            logger.info("Hockey model found at models/hockey_yolo.pt")
    except Exception as e:
        logger.warning(f"Error checking/downloading hockey model: {e}")
    
    # Test database connection
    try:
        client = get_supabase()
        logger.info("Database connection established")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Mount static files directory (for MIDI and other assets)
# Check if we're in backend directory or root
static_path = Path("../") if Path("../Nine_Inch_Nails_-_The_Perfect_Drug.mid").exists() else Path(".")
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for Railway deployment monitoring."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.RAILWAY_ENVIRONMENT
    }


# Root endpoint - Matrix landing page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the Matrix-style landing page."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.exists():
        with open(template_path, "r") as f:
            return HTMLResponse(content=f.read())
    else:
        # Fallback to API info if template not found
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health"
        }

# API info endpoint
@app.get("/api")
async def api_info() -> Dict[str, str]:
    """API endpoint with basic information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Basic upload endpoint (temporary - will be moved to routes)
@app.post("/api/videos/upload")
async def upload_video(
    file: UploadFile = File(...),
    org_id: str = None
) -> ServiceResponse:
    """
    Upload a video file (Phase 1 implementation).
    Will be enhanced with chunked upload and Supabase storage in next phase.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file extension
        allowed_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # For Phase 1, just return success
        # In Phase 2, we'll implement actual file storage
        return ServiceResponse(
            success=True,
            data={
                "filename": file.filename,
                "size": file.size,
                "content_type": file.content_type,
                "message": "File received successfully (Phase 1 - not stored yet)"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return ServiceResponse(
            success=False,
            error=str(e)
        )


# Include routers
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(events.router, prefix="/api/events", tags=["events"])  
app.include_router(organizations.router, prefix="/api/organizations", tags=["organizations"])
app.include_router(ml_processing.router, tags=["ML Processing"])


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )