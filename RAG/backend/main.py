"""
FastAPI main application entry point.
"""
from pathlib import Path
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Project root = parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = PROJECT_ROOT / ".env"
from dotenv import load_dotenv
load_dotenv(dotenv_path=_env_path, override=True)

logger = logging.getLogger(__name__)
logger.info(f"Loading .env from: {_env_path}")
logger.info(f".env exists: {_env_path.exists()}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import routes_auth, routes_chat, routes_docs, routes_admin
from backend.db.session import init_db

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="RAG MVP API",
    description="API for RAG (Retrieval-Augmented Generation) platform",
    version="1.0.0"
)

# CORS configuration
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")  # React frontend; use 8501 para Streamlit
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
# Orígenes extra para CORS (p. ej. ngrok). Comma-separated: CORS_EXTRA_ORIGINS=https://xxx.ngrok-free.app
_cors_extra = os.getenv("CORS_EXTRA_ORIGINS", "")
CORS_EXTRA_ORIGINS = [s.strip() for s in _cors_extra.split(",") if s.strip()]

_cors_origins = [
    FRONTEND_URL,
    "http://localhost:8501",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
] + CORS_EXTRA_ORIGINS

# Permitir orígenes de túneles (ngrok, Cloudflare quick tunnel) sin configurar cada URL.
# Así el frontend en https://xxx.ngrok-free.app o en otro tunnel puede llamar al backend.
CORS_ORIGIN_REGEX = r"https?://[a-z0-9.-]+\.(ngrok-free\.app|ngrok\.io|trycloudflare\.com)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(routes_auth.router)
app.include_router(routes_chat.router)
app.include_router(routes_docs.router)
app.include_router(routes_admin.router)

# Log RAG engine status on startup
try:
    from backend.rag.llamaindex_engine import get_query_engine_status
    rag_status = get_query_engine_status()
    logger.info(f"RAG Engine Status on startup: {rag_status}")
except Exception as e:
    logger.warning(f"Could not check RAG engine status: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "RAG MVP API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
