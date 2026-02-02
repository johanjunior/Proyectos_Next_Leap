"""
Qdrant client for vector similarity search.
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
load_dotenv(dotenv_path=_env_path, override=True)

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_documents")

# Initialize Qdrant client
client = None
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    from qdrant_client.http import models
    
    if QDRANT_URL and QDRANT_API_KEY:
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )
        logger.info(f"Qdrant client initialized successfully. Collection: {QDRANT_COLLECTION}")
    else:
        logger.warning("Qdrant URL or API key not configured")
except ImportError as e:
    logger.error(f"Failed to import Qdrant client: {e}")
except Exception as e:
    logger.error(f"Failed to initialize Qdrant client: {e}")


def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector for a text using OpenAI.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list of floats
    """
    try:
        from openai import OpenAI
        
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI")
        if not api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY or OPENAI in .env")
        
        # Create OpenAI client for embeddings
        openai_client = OpenAI(api_key=api_key)
        
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",  # or "text-embedding-ada-002"
            input=text
        )
        
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def search_similar_documents(
    query: str,
    collection_name: str = None,
    limit: int = 5,
    score_threshold: float = 0.7
) -> List[Dict]:
    """
    Search for similar documents in Qdrant.
    
    Args:
        query: Search query text
        collection_name: Collection name (defaults to QDRANT_COLLECTION)
        limit: Maximum number of results
        score_threshold: Minimum similarity score (0-1)
        
    Returns:
        List of document dictionaries with metadata and scores
    """
    global client
    
    if not client:
        logger.warning("Qdrant client not initialized, returning empty results")
        return []
    
    collection = collection_name or QDRANT_COLLECTION
    
    try:
        # Generate embedding for query
        query_vector = get_embedding(query)
        
        # Search in Qdrant
        search_results = client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Format results
        documents = []
        for result in search_results:
            doc = {
                "document_id": result.id,
                "score": result.score,
                "payload": result.payload or {}
            }
            
            # Extract common fields from payload
            doc["document_name"] = result.payload.get("document_name", f"Document {result.id}")
            doc["snippet"] = result.payload.get("text", result.payload.get("content", ""))
            doc["page_number"] = result.payload.get("page_number")
            doc["metadata"] = result.payload
            
            documents.append(doc)
        
        logger.info(f"Found {len(documents)} similar documents for query")
        return documents
        
    except Exception as e:
        logger.error(f"Error searching Qdrant: {str(e)}")
        return []


def check_collection_exists(collection_name: str = None) -> bool:
    """
    Check if a collection exists in Qdrant.
    
    Args:
        collection_name: Collection name (defaults to QDRANT_COLLECTION)
        
    Returns:
        True if collection exists, False otherwise
    """
    if not client:
        return False
    
    collection = collection_name or QDRANT_COLLECTION
    
    try:
        collections = client.get_collections()
        collection_names = [col.name for col in collections.collections]
        return collection in collection_names
    except Exception as e:
        logger.error(f"Error checking collection: {str(e)}")
        return False
