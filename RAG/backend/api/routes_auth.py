"""
Authentication routes for Google OAuth.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
import os

from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root (same as main.py)
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=_project_root / ".env")

from backend.db.session import get_db, init_db
from backend.db.models import User, ROLE_ADMIN, ROLE_USER
from backend.security.jwt import create_access_token
from backend.security.deps import get_current_user as get_current_user_dep, get_current_user_resolved

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Admins por correo (comma-separated). Ej.: ADMIN_EMAILS=admin@example.com,otro@example.com
_ADMIN_EMAILS = frozenset(
    e.strip().lower() for e in (os.getenv("ADMIN_EMAILS") or "").split(",") if e.strip()
)


def _role_for_email(email: str) -> str:
    return ROLE_ADMIN if email.lower() in _ADMIN_EMAILS else ROLE_USER


class TokenRequest(BaseModel):
    """Request model for token exchange."""
    id_token: str


class TokenResponse(BaseModel):
    """Response model for token exchange."""
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.get("/status")
async def auth_status():
    """
    Debug: comprobar si OAuth está configurado (sin exponer secretos).
    """
    redirect_uri = f"{BACKEND_URL}/auth/callback"
    return {
        "oauth_configured": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
        "redirect_uri": redirect_uri,
        "frontend_url": FRONTEND_URL,
        "backend_url": BACKEND_URL,
    }


@router.get("/login")
async def login():
    """
    Get Google OAuth login URL.
    This endpoint returns the Google OAuth URL for the frontend to redirect to.
    The redirect_uri points to the backend callback endpoint.
    """
    try:
        # Check if OAuth is configured
        if not GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GOOGLE_CLIENT_ID no configurado. Añade GOOGLE_CLIENT_ID en .env (raíz del proyecto)."
            )
        
        if not GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GOOGLE_CLIENT_SECRET no configurado. Añade GOOGLE_CLIENT_SECRET en .env."
            )
        
        # Redirect URI points to backend callback
        redirect_uri = f"{BACKEND_URL}/auth/callback"
        
        # Create OAuth flow
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
            )
            flow.redirect_uri = redirect_uri
            
            # Get authorization URL
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            return {"auth_url": authorization_url, "state": state}
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating OAuth flow: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error in login endpoint: {str(e)}"
        )


@router.get("/callback")
async def oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback from Google.
    Exchanges authorization code for ID token, then creates JWT and redirects to frontend.
    """
    if error:
        # Redirect to frontend with error
        return RedirectResponse(
            url=f"{FRONTEND_URL}?error={error}"
        )
    
    if not code:
        return RedirectResponse(
            url=f"{FRONTEND_URL}?error=no_code"
        )
    
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(
            url=f"{FRONTEND_URL}?error=oauth_not_configured"
        )
    
    try:
        # Create OAuth flow
        redirect_uri = f"{BACKEND_URL}/auth/callback"
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"]
        )
        flow.redirect_uri = redirect_uri
        
        # Exchange code for token
        flow.fetch_token(code=code)
        
        # Get ID token from credentials
        credentials = flow.credentials
        id_token_str = credentials.id_token
        
        if not id_token_str:
            return RedirectResponse(
                url=f"{FRONTEND_URL}?error=no_id_token"
            )
        
        # Verify ID token
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        user_email = idinfo.get("email")
        user_name = idinfo.get("name")
        user_picture = idinfo.get("picture")
        
        if not user_email:
            return RedirectResponse(
                url=f"{FRONTEND_URL}?error=no_email"
            )
        
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                email=user_email,
                name=user_name,
                picture=user_picture,
                is_active=True,
                role=_role_for_email(user_email),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            changed = False
            if user.name != user_name or user.picture != user_picture:
                user.name = user_name
                user.picture = user_picture
                changed = True
            if user_email.lower() in _ADMIN_EMAILS and user.role != ROLE_ADMIN:
                user.role = ROLE_ADMIN
                changed = True
            if changed:
                db.commit()
        
        access_token = create_access_token(
            data={"sub": user_email, "name": user_name, "picture": user_picture}
        )
        return RedirectResponse(url=f"{FRONTEND_URL}?token={access_token}")
        
    except Exception as e:
        from urllib.parse import quote
        err_msg = str(e).replace(" ", "+")[:200]  # avoid huge URLs
        return RedirectResponse(
            url=f"{FRONTEND_URL}?error={quote(err_msg)}"
        )


@router.post("/token", response_model=TokenResponse)
async def exchange_token(
    token_request: TokenRequest,
    db: Session = Depends(get_db)
):
    """
    Exchange Google ID token for JWT access token.
    
    The frontend receives the ID token from Google and sends it here
    to exchange for our own JWT token.
    """
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google OAuth not configured"
        )
    
    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            token_request.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user information
        user_email = idinfo.get("email")
        user_name = idinfo.get("name")
        user_picture = idinfo.get("picture")
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )
        
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            user = User(
                email=user_email,
                name=user_name,
                picture=user_picture,
                is_active=True,
                role=_role_for_email(user_email),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            changed = False
            if user.name != user_name or user.picture != user_picture:
                user.name = user_name
                user.picture = user_picture
                changed = True
            if user_email.lower() in _ADMIN_EMAILS and user.role != ROLE_ADMIN:
                user.role = ROLE_ADMIN
                changed = True
            if changed:
                db.commit()
        
        access_token = create_access_token(
            data={"sub": user_email, "name": user_name, "picture": user_picture}
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user={"email": user_email, "name": user_name, "picture": user_picture},
        )
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user_resolved),
):
    """
    Usuario autenticado con role, permissions, is_active.
    Requiere token válido y usuario no bloqueado.
    """
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token removal).
    """
    return {"message": "Logged out successfully"}
