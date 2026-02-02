"""
Streamlit frontend application for RAG MVP.
"""
import sys
import os

# Add current directory (frontend) to path for imports
# This ensures imports work when running from frontend/ directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import streamlit as st
import requests
from urllib.parse import parse_qs, urlparse
import config
from auth.client import (
    get_auth_url,
    exchange_token,
    verify_google_token,
    get_current_user,
    is_authenticated,
    logout
)
from components.chat import display_chat_interface

# Page configuration
st.set_page_config(
    page_title="RAG MVP - Consulta Documental",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .user-info {
        padding: 0.5rem;
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


def handle_oauth_callback():
    """
    Handle OAuth callback from backend redirect.
    The backend redirects here with a token or error.
    """
    # Get query parameters using new API
    query_params = st.query_params
    
    # Check if we have a token from backend redirect
    token = query_params.get("token")
    
    if token:
        # Store token in session
        st.session_state[config.SESSION_TOKEN_KEY] = token
        
        # Get user info from backend
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{config.BACKEND_URL}/auth/me",
                headers=headers
            )
            if response.status_code == 200:
                user = response.json()
                st.session_state[config.SESSION_USER_KEY] = user
                st.session_state[config.SESSION_AUTHENTICATED_KEY] = True
                
                # Clear query params using new API
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Error al obtener información del usuario.")
        except Exception as e:
            st.error(f"Error al comunicarse con el servidor: {str(e)}")
    
    # Check for error in OAuth flow
    error = query_params.get("error")
    
    if error:
        st.error(f"Error en la autenticación: {error}")
        # Clear error from query params
        st.query_params.clear()


def display_login_page():
    """
    Display login page with Google OAuth button.
    """
    st.markdown('<div class="main-header">🤖 RAG MVP</div>', unsafe_allow_html=True)
    st.markdown("### Consulta Documental Inteligente")
    st.markdown("---")
    
    st.markdown("""
    Bienvenido a la plataforma RAG MVP. Esta aplicación te permite:
    
    - 🔍 Consultar grandes volúmenes de documentos
    - 💬 Hacer preguntas en lenguaje natural
    - 📚 Obtener respuestas fundamentadas con fuentes verificables
    - 🔗 Acceder directamente a los documentos originales
    """)
    
    st.markdown("---")
    
    # Get auth URL
    auth_url = get_auth_url()
    
    if auth_url:
        st.markdown("### Iniciar Sesión")
        st.markdown("Por favor, inicia sesión con tu cuenta de Google para continuar.")
        
        # Use link_button: opens in new tab; OAuth completes there and user lands on app logged in
        st.link_button("🔐 Iniciar sesión con Google", url=auth_url, type="primary")
        st.caption("Se abrirá en una nueva pestaña. Usa la pestaña donde completes el login.")
    else:
        st.warning("No se pudo obtener la URL de login. Revisa el mensaje de error arriba.")


def display_main_app():
    """
    Display main application interface.
    """
    # Sidebar with user info and logout
    with st.sidebar:
        st.markdown("### 👤 Usuario")
        
        user = get_current_user()
        if user:
            st.markdown(f"**Email:** {user.get('email', 'N/A')}")
            if user.get('name'):
                st.markdown(f"**Nombre:** {user.get('name')}")
            if user.get('picture'):
                st.image(user.get('picture'), width=100)
        
        st.markdown("---")
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
        
        st.markdown("---")
        
        # Debug info (can be removed later)
        with st.expander("🔧 Debug Info", expanded=False):
            st.write(f"Messages: {len(st.session_state.get('messages', []))}")
            st.write(f"Conversation ID: {st.session_state.get('conversation_id', 'None')}")
            if st.button("Limpiar historial"):
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ Información")
        st.markdown("""
        Esta aplicación utiliza RAG (Retrieval-Augmented Generation)
        para proporcionar respuestas basadas en documentos.
        """)
    
    # Main content area
    st.markdown('<div class="main-header">🤖 RAG MVP</div>', unsafe_allow_html=True)
    st.markdown("### 💬 Consulta Documental")
    st.markdown("---")
    
    # Display chat interface
    display_chat_interface()


def main():
    """
    Main application entry point.
    """
    # Get query parameters using new API
    query_params = st.query_params
    token = query_params.get("token")
    error = query_params.get("error")
    
    # Handle OAuth callback (token or error from backend redirect)
    if token or error:
        handle_oauth_callback()
        return
    
    # Check authentication
    if not is_authenticated():
        display_login_page()
    else:
        display_main_app()


if __name__ == "__main__":
    main()
