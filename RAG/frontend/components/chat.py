"""
Chat component for Streamlit.
"""
import sys
import os

# Add frontend directory to path for imports
frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if frontend_dir not in sys.path:
    sys.path.insert(0, frontend_dir)

import streamlit as st
import requests
import config
from components.sources import display_sources
from typing import List, Dict, Optional


def display_chat_interface():
    """
    Display the main chat interface.
    """
    # Initialize chat history and conversation_id
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
    
    # Debug: Show message count (temporary, can be removed later)
    # st.sidebar.write(f"Messages in history: {len(st.session_state.messages)}")
    
    # Display chat history FIRST (before input)
    # This ensures all previous messages are shown
    if st.session_state.messages:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Display sources if available (unique key per message to avoid duplicate keys)
                if message.get("sources"):
                    display_sources(message["sources"], key_prefix=f"msg_{i}")
    else:
        # Show welcome message only if no history exists
        with st.chat_message("assistant"):
            st.markdown("¡Hola! Soy tu asistente. ¿En qué puedo ayudarte?")
    
    # Chat input - this triggers on user input
    if prompt := st.chat_input("Escribe tu pregunta aquí..."):
        # Add user message to history IMMEDIATELY (before processing)
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get response from backend
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                try:
                    response_data = send_chat_query(prompt)
                    
                    if response_data:
                        response_text = response_data.get("response", "Error al obtener respuesta")
                        sources = response_data.get("sources", [])
                        
                        # Display response
                        st.markdown(response_text)
                        
                        # Display sources (unique key for new reply; next run it will be in history)
                        if sources:
                            display_sources(sources, key_prefix=f"msg_{len(st.session_state.messages)}")
                        
                        # Add assistant message to history
                        assistant_message = {
                            "role": "assistant",
                            "content": response_text,
                            "sources": sources
                        }
                        st.session_state.messages.append(assistant_message)
                    else:
                        error_msg = "Error al procesar tu consulta. Por favor, intenta de nuevo."
                        st.error(error_msg)
                        assistant_message = {
                            "role": "assistant",
                            "content": error_msg
                        }
                        st.session_state.messages.append(assistant_message)
                except Exception as e:
                    error_msg = f"Error inesperado: {str(e)}"
                    st.error(error_msg)
                    assistant_message = {
                        "role": "assistant",
                        "content": error_msg
                    }
                    st.session_state.messages.append(assistant_message)


def send_chat_query(message: str) -> Optional[Dict]:
    """
    Send chat query to backend API with conversation history.
    
    Args:
        message: User's message
        
    Returns:
        Response dictionary with response and sources, or None if error
    """
    token = st.session_state.get(config.SESSION_TOKEN_KEY)
    if not token:
        st.error("No estás autenticado. Por favor, inicia sesión.")
        return None
    
    # Get conversation history from session (exclude sources for sending to backend)
    messages = st.session_state.get("messages", [])
    conversation_id = st.session_state.get("conversation_id")
    
    # Prepare history for backend (only role and content, no sources)
    history_for_backend = [
        {"role": msg.get("role"), "content": msg.get("content")}
        for msg in messages
        if msg.get("role") and msg.get("content")
    ]
    
    # Prepare request payload with history
    payload = {
        "message": message,
        "conversation_id": conversation_id,
        "history": history_for_backend  # Send history without sources
    }
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{config.BACKEND_URL}/chat/query",
            json=payload,
            headers=headers,
            timeout=config.CHAT_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        
        # Store conversation_id if we got a new one
        if result.get("conversation_id"):
            st.session_state["conversation_id"] = result["conversation_id"]
        
        return result
    except requests.exceptions.Timeout:
        st.error(
            f"La solicitud tardó demasiado (timeout: {config.CHAT_REQUEST_TIMEOUT}s). "
            "Prueba de nuevo o aumenta CHAT_REQUEST_TIMEOUT en .env."
        )
        return None
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = response.json().get("detail", str(e))
        except:
            error_detail = str(e)
        st.error(f"Error del servidor: {error_detail}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Error al comunicarse con el servidor: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error inesperado: {str(e)}")
        return None


