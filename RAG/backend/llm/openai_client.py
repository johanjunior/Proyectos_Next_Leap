"""
OpenAI client for chat interactions.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"

# Log the path being used
logger.info(f"Loading .env from: {_env_path}")
logger.info(f".env exists: {_env_path.exists()}")

# Load environment variables
load_dotenv(dotenv_path=_env_path, override=True)

# Also try loading from current directory as fallback
if not _env_path.exists():
    logger.warning(f".env not found at {_env_path}, trying current directory")
    load_dotenv(override=True)

# OpenAI configuration - check both before and after loading
_openai_key_before = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI")
logger.info(f"OPENAI_API_KEY from env (before explicit load): {_openai_key_before[:20] if _openai_key_before else 'None'}...")

# Reload after explicit dotenv call
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default to gpt-4o-mini for cost efficiency

# Log what we found
if OPENAI_API_KEY:
    logger.info(f"OpenAI API key found: {OPENAI_API_KEY[:20]}... (length: {len(OPENAI_API_KEY)})")
else:
    logger.warning("OpenAI API key NOT found in environment variables")
    # Try to read directly from .env file as debug
    if _env_path.exists():
        try:
            with open(_env_path, 'r') as f:
                content = f.read()
                if 'OPENAI' in content or 'OPENAI_API_KEY' in content:
                    logger.warning(f".env file contains OPENAI variables but they weren't loaded")
                    # Show first 50 chars of lines with OPENAI
                    for line in content.split('\n'):
                        if 'OPENAI' in line:
                            logger.warning(f"Found in .env: {line[:50]}...")
        except Exception as e:
            logger.error(f"Could not read .env file: {e}")

# Initialize OpenAI client
try:
    from openai import OpenAI
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI client initialized successfully")
    else:
        client = None
        logger.warning("OpenAI API key not found in environment variables")
except ImportError as e:
    client = None
    logger.error(f"Failed to import OpenAI: {e}")
except Exception as e:
    client = None
    logger.error(f"Failed to initialize OpenAI client: {e}")


def chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None
) -> str:
    """
    Send a chat completion request to OpenAI.
    
    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model to use (defaults to OPENAI_MODEL from env)
        temperature: Sampling temperature (0-2)
        max_tokens: Maximum tokens in response
        
    Returns:
        Assistant's response text
        
    Raises:
        ValueError: If OpenAI is not configured
        Exception: If API call fails
    """
    global client  # Declare global at the start of the function
    
    # If client is None, try to reload .env and reinitialize
    if not client:
        logger.warning("Client is None, attempting to reload .env and reinitialize")
        load_dotenv(dotenv_path=_env_path, override=True)
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI")
        if api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                logger.info("Successfully reinitialized OpenAI client after reload")
            except Exception as e:
                logger.error(f"Failed to reinitialize client: {e}")
        
        if not client:
            raise ValueError(
                f"OpenAI API key not configured. Set OPENAI_API_KEY or OPENAI in .env. "
                f"Checked path: {_env_path} (exists: {_env_path.exists()})"
            )
    
    if not messages:
        raise ValueError("Messages list cannot be empty")
    
    model = model or OPENAI_MODEL
    
    try:
        logger.info(f"Calling OpenAI API with model: {model}, messages: {len(messages)}")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract response text
        if response.choices and len(response.choices) > 0:
            content = response.choices[0].message.content
            logger.info(f"OpenAI response received: {len(content)} characters")
            return content
        else:
            raise Exception("No response from OpenAI")
            
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise Exception(f"OpenAI API error: {str(e)}")


def format_messages_for_openai(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Format messages for OpenAI API.
    Ensures messages have 'role' and 'content' keys.
    
    Args:
        messages: List of message dicts
        
    Returns:
        Formatted messages list
    """
    formatted = []
    for msg in messages:
        if isinstance(msg, dict) and "role" in msg and "content" in msg:
            formatted.append({
                "role": msg["role"],
                "content": str(msg["content"])
            })
    return formatted
