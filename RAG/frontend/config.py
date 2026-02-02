"""
Configuration for the Streamlit frontend.
"""
import os
from pathlib import Path

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_project_root / ".env")
except Exception:
    pass

# Backend API URL
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

# Frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")

# Chat request timeout (seconds). RAG + Ollama can be slow; increase if you get "tardó demasiado".
CHAT_REQUEST_TIMEOUT = int(os.getenv("CHAT_REQUEST_TIMEOUT", "300"))

# Session state keys
SESSION_TOKEN_KEY = "access_token"
SESSION_USER_KEY = "user"
SESSION_AUTHENTICATED_KEY = "authenticated"
