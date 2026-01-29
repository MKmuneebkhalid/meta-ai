"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.database import Base, engine
from app.api.routes import router
from app.scheduler import DailyJobScheduler
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Meta AI Analyst",
    description="Read-only AI analyst for Meta ad accounts",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Initialize scheduler
scheduler = DailyJobScheduler()


@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler on startup."""
    Base.metadata.create_all(bind=engine)
    scheduler.start()
    logger.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    scheduler.shutdown()
    logger.info("Application stopped")


@app.get("/")
async def root():
    """Serve the web UI or API info."""
    # Try to serve the static HTML file
    static_path = os.path.join(os.path.dirname(__file__), "..", "static", "index.html")
    if os.path.exists(static_path):
        return FileResponse(static_path)
    
    # Fallback to API info
    return {
        "message": "Meta AI Analyst API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "ask": "POST /ask - Ask questions about ad performance",
            "overview": "GET /overview - Get daily overview",
            "snapshot": "POST /snapshot - Trigger data snapshot",
            "snapshots": "GET /snapshots - List historical data",
            "diagnostics": "GET /diagnostics - View diagnostics",
            "health": "GET /health - Health check"
        }
    }


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "message": "Meta AI Analyst API",
        "version": "1.0.0",
        "docs": "/docs"
    }
