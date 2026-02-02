"""
Google OAuth client for Streamlit frontend.
"""
import sys
import os

# Add frontend directory to path for imports
# When running from frontend/, we need to add the frontend directory itself
frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)

import streamlit as st
import requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from typing import Optional, Dict
import config


def get_auth_url() -> str:
    """
    Get Google OAuth authorization URL from backend.
    
    Returns:
        Google OAuth URL, or empty string on error.
    """
    try:
        response = requests.get(f"{config.BACKEND_URL}/auth/login")
        response.raise_for_status()
        data = response.json()
        return data.get("auth_url", "")
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        st.error(f"Backend: {detail}")
        return ""
    except Exception as e:
        st.error(f"No se pudo conectar al backend ({config.BACKEND_URL}). ¿Está en marcha? {e}")
        return ""


def exchange_token(id_token_str: str) -> Optional[Dict]:
    """
    Exchange Google ID token for JWT access token.
    
    Args:
        id_token_str: Google ID token string
        
    Returns:
        Dictionary with access_token and user info, or None if error
    """
    try:
        response = requests.post(
            f"{config.BACKEND_URL}/auth/token",
            json={"id_token": id_token_str}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error exchanging token: {str(e)}")
        return None


def verify_google_token(id_token_str: str) -> Optional[Dict]:
    """
    Verify Google ID token locally (client-side verification).
    
    Args:
        id_token_str: Google ID token string
        
    Returns:
        Decoded token payload or None if invalid
    """
    try:
        if not config.GOOGLE_CLIENT_ID:
            return None
        
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            config.GOOGLE_CLIENT_ID
        )
        return idinfo
    except ValueError:
        return None


def get_current_user() -> Optional[Dict]:
    """
    Get current authenticated user from session or API.
    
    Returns:
        User dictionary or None if not authenticated
    """
    if not st.session_state.get(config.SESSION_AUTHENTICATED_KEY, False):
        return None
    
    # Try to get from session first
    user = st.session_state.get(config.SESSION_USER_KEY)
    if user:
        return user
    
    # If not in session, try to get from API
    token = st.session_state.get(config.SESSION_TOKEN_KEY)
    if not token:
        return None
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{config.BACKEND_URL}/auth/me",
            headers=headers
        )
        if response.status_code == 200:
            user = response.json()
            st.session_state[config.SESSION_USER_KEY] = user
            return user
    except Exception:
        pass
    
    return None


def is_authenticated() -> bool:
    """
    Check if user is authenticated.
    
    Returns:
        True if authenticated, False otherwise
    """
    return st.session_state.get(config.SESSION_AUTHENTICATED_KEY, False)


def logout():
    """
    Logout current user by clearing session state.
    """
    st.session_state[config.SESSION_TOKEN_KEY] = None
    st.session_state[config.SESSION_USER_KEY] = None
    st.session_state[config.SESSION_AUTHENTICATED_KEY] = False
    st.session_state["messages"] = []  # Clear chat history
    st.rerun()
