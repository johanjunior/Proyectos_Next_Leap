"""
LlamaIndex RAG Engine - Central orchestrator for RAG workflow.
Integrates Qdrant vector store with Google Gemini LLM.
"""
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Load .env from project root
_project_root = Path(__file__).resolve().parent.parent.parent
_env_path = _project_root / ".env"
load_dotenv(dotenv_path=_env_path, override=True)

logger.info(f"Loading .env from: {_env_path}")
logger.info(f".env exists: {_env_path.exists()}")

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "rag_documents")

# Hetzner S3 Configuration (for PDF signed URLs)
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

# Google Gemini configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Ollama configuration (local)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:14b")
# Timeout en milisegundos para llamadas a Ollama. Modelos como deepseek-r1 pueden tardar 1-3 min.
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180000"))  # default: 3 minutos

# Debug: Log configuration status
logger.info("=" * 70)
logger.info("🔧 Configuration Status")
logger.info("=" * 70)
logger.info(f"   QDRANT_URL: {'SET' if QDRANT_URL else 'NOT SET'}")
logger.info(f"   QDRANT_API_KEY: {'SET' if QDRANT_API_KEY else 'NOT SET'}")
logger.info(f"   GEMINI_API_KEY: {'SET' if GEMINI_API_KEY else 'NOT SET'}")
logger.info(f"   GEMINI_MODEL: {GEMINI_MODEL}")
logger.info(f"   S3_ENDPOINT: {'SET' if S3_ENDPOINT else 'NOT SET'} ({S3_ENDPOINT if S3_ENDPOINT else 'N/A'})")
logger.info(f"   S3_BUCKET: {'SET' if S3_BUCKET else 'NOT SET'} ({S3_BUCKET if S3_BUCKET else 'N/A'})")
logger.info(f"   S3_ACCESS_KEY: {'SET' if S3_ACCESS_KEY else 'NOT SET'}")
logger.info(f"   S3_SECRET_KEY: {'SET' if S3_SECRET_KEY else 'NOT SET'}")
logger.info("=" * 70)

# Performance configuration
QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "30"))  # Timeout in seconds for Qdrant operations
SIMILARITY_TOP_K = int(os.getenv("SIMILARITY_TOP_K", "3"))  # Number of chunks to retrieve (reduced from 5 for speed)
CONVERSATION_HISTORY_LIMIT = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "3"))  # Max messages in history (reduced from 5)
SIMILARITY_SCORE_THRESHOLD = float(os.getenv("SIMILARITY_SCORE_THRESHOLD", "0.5"))  # Minimum similarity score to include sources (0.0-1.0)
# Filtrado por metadata (nombre, sede, etc.): requiere índices keyword en Qdrant. Si False, solo búsqueda vectorial.
USE_METADATA_FILTER = os.getenv("USE_METADATA_FILTER", "false").lower() in ("1", "true", "yes")
# Interpretar la consulta antes de recuperar: si no requiere documentos (saludo, sin sentido, off-topic), no se hace OCR/retrieval.
QUERY_INTENT_CHECK = os.getenv("QUERY_INTENT_CHECK", "true").lower() in ("1", "true", "yes")

# Hybrid Search: combina búsqueda vectorial con BM25 para capturar tanto similitud semántica como keywords exactos.
HYBRID_SEARCH_ENABLED = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() in ("1", "true", "yes")
# Alpha: peso de la búsqueda vectorial (1-alpha = peso de BM25). 0.7 = 70% vectorial, 30% BM25.
HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.7"))
# Candidatos iniciales a recuperar con búsqueda vectorial (antes del reranking BM25).
HYBRID_INITIAL_TOP_K = int(os.getenv("HYBRID_INITIAL_TOP_K", "15"))

# Initialize components
query_engine = None
query_engine_ollama = None
vector_store = None
llm = None  # Default LLM (Gemini)
llm_gemini = None
llm_ollama = None
embed_model = None
index = None  # VectorStoreIndex for creating dynamic retrievers with filters

try:
    from llama_index.core import VectorStoreIndex, Settings
    from llama_index.vector_stores.qdrant import QdrantVectorStore
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.response_synthesizers import ResponseMode
    
    # Try to import Google Gemini LLM
    try:
        from llama_index.llms.google_genai import GoogleGenAI
        GEMINI_AVAILABLE = True
        logger.info("✅ Google GenAI (Gemini) LLM module imported successfully")
    except ImportError:
        GEMINI_AVAILABLE = False
        logger.warning("⚠️  llama-index-llms-google-genai not installed")
        logger.warning("   Install with: pip install llama-index-llms-google-genai")
        GoogleGenAI = None

    # Try to import Ollama LLM
    try:
        from llama_index.llms.ollama import Ollama
        OLLAMA_AVAILABLE = True
        logger.info("✅ Ollama LLM module imported successfully")
    except ImportError:
        OLLAMA_AVAILABLE = False
        logger.warning("⚠️  llama-index-llms-ollama not installed")
        logger.warning("   Install with: pip install llama-index-llms-ollama")
        Ollama = None
    
    # Try to import HuggingFace embeddings (optional dependency)
    try:
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        HUGGINGFACE_AVAILABLE = True
        logger.info("✅ HuggingFace embeddings module imported successfully")
    except ImportError:
        HUGGINGFACE_AVAILABLE = False
        logger.warning("⚠️  llama-index-embeddings-huggingface not installed")
        logger.warning("   Install with: pip install llama-index-embeddings-huggingface")
        HuggingFaceEmbedding = None
    
    logger.info("LlamaIndex core imports successful")
    
    # Initialize Google Gemini LLM
    logger.info("=" * 70)
    logger.info("🔧 Initializing Google Gemini LLM")
    logger.info("=" * 70)
    logger.info(f"   Model: {GEMINI_MODEL}")
    logger.info(f"   API Key: {'SET' if GEMINI_API_KEY else 'NOT SET'}")
    
    if not GEMINI_AVAILABLE:
        llm_gemini = None
        logger.error("❌ Google GenAI (Gemini) LLM module not available")
        logger.error("   Install with: pip install llama-index-llms-google-genai")
        logger.error("   Or run: pip install -r requirements.txt")
    elif not GEMINI_API_KEY:
        llm_gemini = None
        logger.error("❌ GEMINI_API_KEY (or GOOGLE_API_KEY) not configured in .env")
        logger.error("   Add GEMINI_API_KEY=your-key to .env (from Google AI Studio)")
    else:
        logger.info("🚀 Creating Google Gemini LLM client...")
        try:
            llm_gemini = GoogleGenAI(
                model=GEMINI_MODEL,
                api_key=GEMINI_API_KEY,
                temperature=0.7,
            )
            Settings.llm = llm_gemini
            logger.info(f"✅ Google Gemini LLM initialized successfully")
            logger.info(f"   - Model: {GEMINI_MODEL}")
            logger.info(f"   - Temperature: 0.7")
        except Exception as e:
            llm_gemini = None
            logger.error(f"❌ Failed to initialize Google Gemini LLM: {e}")
            import traceback
            logger.error(traceback.format_exc())
            logger.error("   Check GEMINI_API_KEY in .env and model name (e.g. gemini-2.0-flash)")
    
    # Initialize Ollama LLM (local)
    logger.info("=" * 70)
    logger.info("🔧 Initializing Ollama LLM")
    logger.info("=" * 70)
    logger.info(f"   Base URL: {OLLAMA_BASE_URL}")
    logger.info(f"   Model: {OLLAMA_MODEL}")
    logger.info(f"   Timeout: {OLLAMA_TIMEOUT}ms ({OLLAMA_TIMEOUT/1000:.0f}s)")
    
    if not OLLAMA_AVAILABLE:
        llm_ollama = None
        logger.warning("⚠️  Ollama LLM module not available. Install with: pip install llama-index-llms-ollama")
    else:
        try:
            llm_ollama = Ollama(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                request_timeout=OLLAMA_TIMEOUT / 1000.0,  # Convert ms to seconds
                temperature=0.7,
            )
            logger.info("✅ Ollama LLM initialized successfully")
        except Exception as e:
            llm_ollama = None
            logger.warning(f"⚠️  Could not initialize Ollama LLM: {e}")
            logger.warning("   Ensure Ollama is running: ollama serve && ollama pull " + OLLAMA_MODEL)
    
    llm = llm_gemini or llm_ollama  # Default LLM: Gemini si disponible, sino Ollama
    
    logger.info("=" * 70)
    
    # Initialize Sentence Transformers Embeddings via HuggingFace (local, no API needed)
    logger.info("=" * 70)
    logger.info("🔧 Initializing Embedding Model")
    logger.info("=" * 70)
    embed_model_name = os.getenv("EMBED_MODEL", "hiiamsid/sentence_similarity_spanish_es")
    logger.info(f"   Model: {embed_model_name}")
    
    if not HUGGINGFACE_AVAILABLE:
        embed_model = None
        logger.error(f"❌ Cannot load embedding model: HuggingFace module not available")
        logger.error("   Install with: pip install llama-index-embeddings-huggingface")
        logger.error("   Or run: pip install -r requirements.txt")
    else:
        logger.info("   (This may take a few seconds on first load to download the model)")
        try:
            embed_model = HuggingFaceEmbedding(
                model_name=embed_model_name,
                device="cpu",  # Use "cuda" if you have GPU
                normalize=True,
            )
            Settings.embed_model = embed_model
            # Get vector dimension by encoding a test string
            test_embedding = embed_model.get_query_embedding("test")
            vector_dim = len(test_embedding)
            logger.info(f"✅ Embedding model loaded successfully")
            logger.info(f"   - Model: {embed_model_name}")
            logger.info(f"   - Dimensions: {vector_dim}")
        except Exception as e:
            embed_model = None
            logger.error(f"❌ Failed to load embedding model '{embed_model_name}': {e}")
            logger.error("   Make sure 'llama-index-embeddings-huggingface' is installed: pip install llama-index-embeddings-huggingface")
            import traceback
            logger.error(traceback.format_exc())
    
    logger.info("=" * 70)
    
    # Initialize Qdrant Vector Store
    if QDRANT_URL and QDRANT_API_KEY:
        from qdrant_client import QdrantClient
        
        logger.info(f"Connecting to Qdrant: {QDRANT_URL[:50]}... (timeout: {QDRANT_TIMEOUT}s)")
        logger.info(f"Qdrant API Key found: {QDRANT_API_KEY[:10]}...{QDRANT_API_KEY[-4:] if len(QDRANT_API_KEY) > 14 else '***'}")
        
        try:
            qdrant_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                timeout=QDRANT_TIMEOUT,  # Add timeout to prevent hanging
            )
            
            vector_store = QdrantVectorStore(
                client=qdrant_client,
                collection_name=QDRANT_COLLECTION,
            )
            
            logger.info(f"✅ Qdrant Vector Store initialized: {QDRANT_COLLECTION}")
        except Exception as e:
            vector_store = None
            logger.error(f"❌ Failed to connect to Qdrant: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        vector_store = None
        logger.warning(f"⚠️  Qdrant not configured: URL={bool(QDRANT_URL)}, API_KEY={bool(QDRANT_API_KEY)}")
    
    # Create Vector Store Index (only if vector_store, embed_model, and llm are available)
    logger.info("=" * 70)
    logger.info("🔍 Checking components for query engine initialization...")
    logger.info("=" * 70)
    logger.info(f"   ✓ vector_store: {vector_store is not None} {'✅' if vector_store else '❌'}")
    logger.info(f"   ✓ embed_model: {embed_model is not None} {'✅' if embed_model else '❌'}")
    logger.info(f"   ✓ llm: {llm is not None} {'✅' if llm else '❌'}")
    logger.info("=" * 70)
    
    if vector_store and embed_model and llm:
        logger.info("Creating Vector Store Index...")
        try:
            # No need for 'global' here - we're at module level
            index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=embed_model
            )
            logger.info("✅ Vector Store Index created")
            
            # Create Query Engine with retriever
            logger.info("Creating Query Engine...")
            retriever = VectorIndexRetriever(
                index=index,
                similarity_top_k=SIMILARITY_TOP_K,  # Optimized: reduced from 5 to 3 for faster retrieval
            )
            
            # Use SIMPLE_SUMMARIZE instead of COMPACT for better performance
            # COMPACT mode does more processing and is slower (~1-3s slower)
            query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                llm=llm,
                response_mode=ResponseMode.SIMPLE_SUMMARIZE,  # Faster than COMPACT mode
            )
            
            # Create Ollama query engine if Ollama LLM is available
            query_engine_ollama = None
            if llm_ollama is not None:
                try:
                    retriever_ollama = VectorIndexRetriever(
                        index=index,
                        similarity_top_k=SIMILARITY_TOP_K,
                    )
                    query_engine_ollama = RetrieverQueryEngine.from_args(
                        retriever=retriever_ollama,
                        llm=llm_ollama,
                        response_mode=ResponseMode.SIMPLE_SUMMARIZE,
                    )
                    logger.info(f"   - Ollama Query Engine: {OLLAMA_MODEL} ✅")
                except Exception as e:
                    logger.warning(f"   - Ollama Query Engine: failed ({e})")
            else:
                query_engine_ollama = None
            
            logger.info("=" * 70)
            logger.info("✅ LlamaIndex Query Engine initialized successfully")
            logger.info("=" * 70)
            logger.info(f"   - LLM Gemini: {GEMINI_MODEL} ✅")
            logger.info(f"   - Embedding: {embed_model_name}")
            logger.info(f"   - Similarity Top K: {SIMILARITY_TOP_K}")
            logger.info(f"   - Collection: {QDRANT_COLLECTION}")
            logger.info(f"   - Qdrant URL: {QDRANT_URL[:50] if QDRANT_URL else 'N/A'}...")
            logger.info("=" * 70)
        except Exception as e:
            query_engine = None
            query_engine_ollama = None
            logger.error(f"❌ Failed to create query engine: {e}")
            import traceback
            logger.error(traceback.format_exc())
    else:
        query_engine = None
        query_engine_ollama = None
        logger.warning("=" * 70)
        logger.warning("⚠️  Cannot create query engine - Missing components:")
        logger.warning("=" * 70)
        logger.warning(f"   - vector_store: {vector_store is not None} (required: True)")
        logger.warning(f"   - embed_model: {embed_model is not None} (required: True)")
        logger.warning(f"   - llm: {llm is not None} (required: True)")
        logger.warning("=" * 70)
        
        # Provide specific guidance
        missing_components = []
        if not vector_store:
            missing_components.append("vector_store")
            logger.warning("   ❌ vector_store missing")
            logger.warning("      → Fix: Check QDRANT_URL and QDRANT_API_KEY in .env")
        if not embed_model:
            missing_components.append("embed_model")
            logger.warning("   ❌ embed_model missing")
            logger.warning("      → Fix: Install llama-index-embeddings-huggingface")
            logger.warning("        Run: pip install llama-index-embeddings-huggingface")
        if not llm:
            missing_components.append("llm")
            logger.warning("   ❌ llm missing")
            logger.warning("      → Fix: Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")
            logger.warning(f"        Model: {GEMINI_MODEL} (e.g. gemini-2.0-flash)")
            logger.warning("        Get key from: https://aistudio.google.com/app/apikey")
        
        logger.warning("=" * 70)
        logger.warning(f"⚠️  Query engine will not be available until all components are initialized")
        logger.warning("=" * 70)
        
except ImportError as e:
    logger.error("=" * 70)
    logger.error("❌ Failed to import LlamaIndex components")
    logger.error("=" * 70)
    logger.error(f"Error: {e}")
    logger.error("")
    logger.error("Required packages:")
    logger.error("  - llama-index")
    logger.error("  - llama-index-vector-stores-qdrant")
    logger.error("  - llama-index-llms-openai")
    logger.error("  - llama-index-embeddings-huggingface (for embeddings)")
    logger.error("")
    logger.error("Install with: pip install -r requirements.txt")
    import traceback
    logger.error(traceback.format_exc())
except Exception as e:
    logger.error("=" * 70)
    logger.error("❌ Failed to initialize LlamaIndex engine")
    logger.error("=" * 70)
    logger.error(f"Error: {e}")
    import traceback
    logger.error(traceback.format_exc())


# ============================================================================
# LLM Provider Selection
# ============================================================================

def get_llm_for_provider(provider: str):
    """
    Retorna el LLM correspondiente al proveedor indicado.
    provider: 'gemini' | 'ollama'
    """
    global llm_gemini, llm_ollama
    provider_lower = (provider or "gemini").lower().strip()
    if provider_lower == "ollama" and llm_ollama is not None:
        return llm_ollama
    # Default: Gemini (o el que esté disponible)
    return llm_gemini or llm_ollama


def get_query_engine_for_provider(provider: str):
    """
    Retorna el query engine correspondiente al proveedor.
    provider: 'gemini' | 'ollama'
    """
    global query_engine, query_engine_ollama
    provider_lower = (provider or "gemini").lower().strip()
    if provider_lower == "ollama" and query_engine_ollama is not None:
        return query_engine_ollama
    return query_engine


# ============================================================================
# HYBRID SEARCH: BM25 Reranking
# ============================================================================

def _tokenize_spanish(text: str) -> List[str]:
    """
    Tokeniza texto en español para BM25.
    Elimina puntuación, convierte a minúsculas, y filtra stopwords comunes.
    """
    import unicodedata
    # Normalizar y convertir a minúsculas
    text = unicodedata.normalize('NFKD', text.lower())
    # Eliminar acentos para matching más flexible
    text_no_accents = ''.join(c for c in text if not unicodedata.combining(c))
    # Tokenizar por espacios y caracteres no alfanuméricos
    tokens = re.split(r'[^\w]+', text_no_accents)
    # Filtrar tokens vacíos y stopwords comunes en español
    stopwords_es = {
        'de', 'la', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por',
        'un', 'para', 'con', 'no', 'una', 'su', 'al', 'es', 'lo', 'como',
        'mas', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'si', 'porque', 'esta',
        'entre', 'cuando', 'muy', 'sin', 'sobre', 'ser', 'tiene', 'tambien',
        'me', 'hasta', 'hay', 'donde', 'han', 'quien', 'estan', 'estado',
        'desde', 'todo', 'nos', 'durante', 'estados', 'todos', 'uno', 'les',
        'ni', 'contra', 'otros', 'fueron', 'ese', 'eso', 'habia', 'ante',
        'ellos', 'e', 'esto', 'mi', 'antes', 'algunos', 'que', 'cual', 'fue'
    }
    return [t for t in tokens if t and len(t) > 1 and t not in stopwords_es]


def _bm25_rerank_nodes(query: str, nodes: List[Any], top_k: int = None) -> List[Any]:
    """
    Aplica BM25 reranking sobre nodos recuperados por búsqueda vectorial.
    Combina el score vectorial con el score BM25 para mejor ranking.
    
    Args:
        query: La consulta del usuario
        nodes: Lista de nodos de LlamaIndex (con .score y .node.text o .text)
        top_k: Número de nodos a devolver (None = todos)
    
    Returns:
        Lista de nodos reordenados por score híbrido (vectorial + BM25)
    """
    if not nodes:
        return nodes
    
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.warning("⚠️  rank_bm25 not installed. Skipping BM25 reranking. Install with: pip install rank_bm25")
        return nodes[:top_k] if top_k else nodes
    
    # Extraer textos de los nodos
    node_texts = []
    for node in nodes:
        actual_node = node.node if hasattr(node, 'node') and node.node else node
        text = ""
        if hasattr(actual_node, 'text') and actual_node.text:
            text = actual_node.text
        elif hasattr(node, 'text') and node.text:
            text = node.text
        node_texts.append(text)
    
    # Tokenizar para BM25
    tokenized_corpus = [_tokenize_spanish(text) for text in node_texts]
    tokenized_query = _tokenize_spanish(query)
    
    if not tokenized_query or not any(tokenized_corpus):
        logger.debug("⚠️  Empty tokens for BM25. Returning original order.")
        return nodes[:top_k] if top_k else nodes
    
    # Crear índice BM25 y obtener scores
    try:
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(tokenized_query)
    except Exception as e:
        logger.warning(f"⚠️  BM25 scoring failed: {e}. Returning original order.")
        return nodes[:top_k] if top_k else nodes
    
    # Normalizar scores BM25 a rango [0, 1]
    max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0
    bm25_scores_norm = [s / max_bm25 for s in bm25_scores]
    
    # Combinar scores: hybrid_score = alpha * vector_score + (1 - alpha) * bm25_score
    hybrid_results = []
    for i, node in enumerate(nodes):
        vector_score = node.score if hasattr(node, 'score') and node.score is not None else 0.0
        bm25_score = bm25_scores_norm[i]
        hybrid_score = HYBRID_ALPHA * vector_score + (1 - HYBRID_ALPHA) * bm25_score
        
        # Crear copia del nodo con el nuevo score
        # (usamos un wrapper simple para no modificar el nodo original)
        hybrid_results.append({
            'node': node,
            'vector_score': vector_score,
            'bm25_score': bm25_score,
            'hybrid_score': hybrid_score,
        })
    
    # Ordenar por score híbrido descendente
    hybrid_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
    
    # Log de reranking para debug
    if hybrid_results:
        logger.info(f"🔀 Hybrid Search Reranking (alpha={HYBRID_ALPHA}):")
        for i, r in enumerate(hybrid_results[:5]):  # Log top 5
            node = r['node']
            actual_node = node.node if hasattr(node, 'node') and node.node else node
            doc_name = "Unknown"
            if hasattr(actual_node, 'metadata') and actual_node.metadata:
                doc_name = actual_node.metadata.get('nombre', 'Unknown')[:40]
            logger.info(f"   {i+1}. {doc_name}... | vec={r['vector_score']:.3f} | bm25={r['bm25_score']:.3f} | hybrid={r['hybrid_score']:.3f}")
    
    # Devolver nodos reordenados
    reranked_nodes = [r['node'] for r in hybrid_results]
    
    if top_k:
        return reranked_nodes[:top_k]
    return reranked_nodes


def extract_metadata_from_query(query: str) -> Dict[str, Optional[str]]:
    """
    Extrae metadata relevante de la consulta del usuario para los 6 campos del payload.
    
    Campos: nombre, radicado, sede, tipo_proceso, demandante, demandado.
    Se intenta extraer toda la información relevante del prompt para cada uno.
    
    Args:
        query: Consulta del usuario
        
    Returns:
        Diccionario con metadata extraída (valores None si no se encontraron)
    """
    query_lower = query.lower()
    metadata = {
        "nombre": None,
        "radicado": None,
        "sede": None,
        "tipo_proceso": None,
        "demandante": None,
        "demandado": None
    }
    
    sede_keywords = {
        "sede principal": "Sede Principal",
        "bogotá": "Bogotá", "bogota": "Bogotá",
        "medellín": "Medellín", "medellin": "Medellín",
        "cali": "Cali", "barranquilla": "Barranquilla", "cartagena": "Cartagena",
        "florencia": "Florencia", "pereira": "Pereira", "manizales": "Manizales",
        "armenia": "Armenia", "ibagué": "Ibagué", "ibague": "Ibagué",
        "pasto": "Pasto", "neiva": "Neiva", "villavicencio": "Villavicencio",
        "bucaramanga": "Bucaramanga", "santa marta": "Santa Marta",
        "valledupar": "Valledupar", "montería": "Montería", "monteria": "Montería",
    }
    
    # --- Radicado ---
    radicado_patterns = [
        r'\b(\d{3,4}[- ]?RAD[- ]?\d{4}[- ]?\d{5}[- ]?\d{2})\b',
        r'\b(RAD[- ]?\d{4}[- ]?\d{5})\b',
        r'\b(\d{3,4}[- ]?\d{4}[- ]?\d{5}[- ]?\d{2})\b',
    ]
    for pat in radicado_patterns:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            metadata["radicado"] = m.group(1).strip()
            break
    
    # --- Tipo proceso ---
    tipo_keywords = {
        "reparación directa": "Reparacion directa", "reparacion directa": "Reparacion directa",
        "reparación": "Reparacion directa", "tutela": "Tutela",
        "acción de tutela": "Tutela", "accion de tutela": "Tutela",
        "acción de grupo": "Accion de grupo", "accion de grupo": "Accion de grupo",
        "acción popular": "Accion popular", "accion popular": "Accion popular",
        "cumplimiento": "Cumplimiento", "acción de cumplimiento": "Cumplimiento",
    }
    for kw, tipo in tipo_keywords.items():
        if kw in query_lower:
            metadata["tipo_proceso"] = tipo
            break
    
    # --- Sede ---
    for kw, sede in sede_keywords.items():
        if kw in query_lower:
            metadata["sede"] = sede
            break
    
    # --- Demandante / Demandado: "caso de X [contra Y]", "demandante X", "demandado Y", "contra Y", etc. ---
    # "caso de la señora Rebeca en Florencia" -> demandante Rebeca, sede Florencia
    # "caso de Rebeca contra Fiscalía" -> demandante Rebeca, demandado Fiscalía
    caso_contra = re.search(
        r'\bcaso\s+(?:del|de la|de)\s+(?:señor|señora|sr\.?|sra\.?)?\s*'
        r'([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)\s+contra\s+'
        r'([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$|\sen\b)',
        query, re.IGNORECASE
    )
    if caso_contra:
        d1 = re.sub(r'^(señor|señora|sr\.?|sra\.?)\s+', '', caso_contra.group(1).strip(), flags=re.IGNORECASE).strip()
        d2 = caso_contra.group(2).strip()
        if len(d1) > 2 and d1.lower() not in {s.lower() for s in sede_keywords.values()}:
            metadata["demandante"] = d1
        if len(d2) > 2 and d2.lower() not in {s.lower() for s in sede_keywords.values()}:
            metadata["demandado"] = d2
    
    # Demandante explícito
    for pat in [
        r'\bdemandante[:\s]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$|\bdemandado|\bcontra|\ben)',
        r'\bactor[:\s]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$|\bdemandado|\bcontra|\ben)',
    ]:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            v = re.sub(r'^(señor|señora|sr\.?|sra\.?)\s+', '', m.group(1).strip(), flags=re.IGNORECASE).strip()
            if len(v) > 2:
                metadata["demandante"] = metadata["demandante"] or v
                break
    
    # Demandado explícito
    for pat in [
        r'\bdemandado[:\s]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$|\bdemandante|\bactor|\ben)',
        r'\bcontra[:\s]+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$|\ben\b)',
        r'\bvs\.?\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?:\.|,|$)',
    ]:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            v = m.group(1).strip()
            if len(v) > 2 and v.lower() not in {s.lower() for s in sede_keywords.values()}:
                metadata["demandado"] = metadata["demandado"] or v
                break
    
    # Demandante desde "caso de [nombre]" o "señor/señora [nombre]" (si no hay contra Y)
    if not metadata.get("demandante"):
        for pat in [
            r'\bcaso\s+(?:del|de la|de)\s+(?:señor|señora|sr\.?|sra\.?)?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
            r'\b(?:señor|señora|sr\.?|sra\.?)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
        ]:
            m = re.search(pat, query, re.IGNORECASE)
            if m:
                v = re.sub(r'^(señor|señora|sr\.?|sra\.?)\s+', '', m.group(1).strip(), flags=re.IGNORECASE).strip()
                if len(v) > 2 and v.lower() not in {s.lower() for s in sede_keywords.values()}:
                    metadata["demandante"] = v
                    break
    
    # Demandado: entidades típicas (Fiscalía, DAS, etc.) si aparecen en el texto
    org_keywords = {
        "fiscalía": "Fiscalía", "fiscalia": "Fiscalía",
        "das": "DAS", "d.as": "DAS",
        "nación": "Nación", "nacion": "Nación",
        "rama judicial": "Rama Judicial", "ministerio público": "Ministerio Público",
        "contraloría": "Contraloría", "contraloria": "Contraloría",
        "procuraduría": "Procuraduría", "procuraduria": "Procuraduría",
    }
    if not metadata.get("demandado"):
        for kw, org in org_keywords.items():
            if kw in query_lower:
                metadata["demandado"] = org
                break
    
    # --- Nombre (expediente/caso entre comillas o después de etiquetas) ---
    for pat in [
        r'[""]([^""]+)[""]',
        r'\bexpediente[:\s]+([A-ZÁÉÍÓÚÑ][^,\.]+?)(?:\.|,|$)',
        r'\bcaso[:\s]+([A-ZÁÉÍÓÚÑ][^,\.]+?)(?:\.|,|$)',
    ]:
        m = re.search(pat, query, re.IGNORECASE)
        if m:
            v = m.group(1).strip()
            if len(v) > 3:
                metadata["nombre"] = v
                break
    
    extracted = {k: v for k, v in metadata.items() if v is not None}
    if extracted:
        logger.info(f"📋 Metadata extraída de la consulta: {extracted}")
    else:
        logger.debug("📋 No se extrajo metadata específica de la consulta")
    
    return metadata


# Sinónimos para MatchAny: un valor en payload puede estar guardado de varias formas.
# Ver https://qdrant.tech/documentation/concepts/filtering/#match-any
_METADATA_SYNONYMS: Dict[str, Dict[str, List[str]]] = {
    "sede": {
        "Bogotá": ["Bogotá", "Bogota"],
        "Medellín": ["Medellín", "Medellin"],
        "Ibagué": ["Ibagué", "Ibague"],
        "Montería": ["Montería", "Monteria"],
        "Reparacion directa": ["Reparación directa", "Reparacion directa"],
    },
    "tipo_proceso": {
        "Reparacion directa": ["Reparación directa", "Reparacion directa"],
        "Accion de grupo": ["Acción de grupo", "Accion de grupo"],
        "Accion popular": ["Acción popular", "Accion popular"],
    },
    "demandado": {
        "Fiscalía": ["Fiscalía", "Fiscalia"],
        "Nación": ["Nación", "Nacion"],
        "Contraloría": ["Contraloría", "Contraloria"],
        "Procuraduría": ["Procuraduría", "Procuraduria"],
    },
}


def _match_for_value(key: str, value: str) -> Any:
    """Construye MatchValue o MatchAny si hay sinónimos (optimización Qdrant)."""
    try:
        from qdrant_client.http.models import MatchValue, MatchAny
    except ImportError:
        return None
    synonyms_map = _METADATA_SYNONYMS.get(key, {})
    alternatives = synonyms_map.get(value, [value])
    if len(alternatives) <= 1:
        return MatchValue(value=value)
    # Evitar duplicados y mantener orden
    seen = set()
    unique = []
    for x in alternatives:
        x_lower = x.lower()
        if x_lower not in seen:
            seen.add(x_lower)
            unique.append(x)
    return MatchAny(any=unique)


def build_qdrant_filter(metadata: Dict[str, Optional[str]]) -> Optional[Any]:
    """
    Construye un filtro Qdrant basado en metadata extraída.
    Usa MatchAny para campos con sinónimos (sede, tipo_proceso, demandado) para mejorar recall.
    
    Args:
        metadata: Diccionario con metadata (nombre, radicado, sede, tipo_proceso, demandante, demandado)
        
    Returns:
        Filter de Qdrant o None si no hay metadata para filtrar
    """
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    except ImportError:
        logger.warning("⚠️  qdrant_client no disponible para construir filtros")
        return None
    
    conditions = []
    
    if metadata.get("nombre"):
        conditions.append(
            FieldCondition(key="nombre", match=MatchValue(value=metadata["nombre"]))
        )
    
    if metadata.get("radicado"):
        conditions.append(
            FieldCondition(key="radicado", match=MatchValue(value=metadata["radicado"]))
        )
    
    if metadata.get("sede"):
        match = _match_for_value("sede", metadata["sede"])
        if match:
            conditions.append(FieldCondition(key="sede", match=match))
        else:
            conditions.append(
                FieldCondition(key="sede", match=MatchValue(value=metadata["sede"]))
            )
    
    if metadata.get("tipo_proceso"):
        match = _match_for_value("tipo_proceso", metadata["tipo_proceso"])
        if match:
            conditions.append(FieldCondition(key="tipo_proceso", match=match))
        else:
            conditions.append(
                FieldCondition(
                    key="tipo_proceso",
                    match=MatchValue(value=metadata["tipo_proceso"]),
                )
            )
    
    if metadata.get("demandante"):
        match = _match_for_value("demandante", metadata["demandante"])
        if match:
            conditions.append(FieldCondition(key="demandante", match=match))
        else:
            conditions.append(
                FieldCondition(
                    key="demandante",
                    match=MatchValue(value=metadata["demandante"]),
                )
            )
        logger.debug(f"🔍 Filtro demandante: '{metadata['demandante']}'")
    
    if metadata.get("demandado"):
        match = _match_for_value("demandado", metadata["demandado"])
        if match:
            conditions.append(FieldCondition(key="demandado", match=match))
        else:
            conditions.append(
                FieldCondition(
                    key="demandado",
                    match=MatchValue(value=metadata["demandado"]),
                )
            )
        logger.debug(f"🔍 Filtro demandado: '{metadata['demandado']}'")
    
    if not conditions:
        return None
    
    qdrant_filter = Filter(must=conditions)
    logger.info(f"🔍 Filtro Qdrant construido con {len(conditions)} condiciones")
    return qdrant_filter


def _conditions_for_metadata(
    metadata: Dict[str, Optional[str]],
) -> List[Any]:
    """Construye lista de FieldConditions; usa MatchAny para campos con sinónimos."""
    try:
        from qdrant_client.http.models import FieldCondition, MatchValue
    except ImportError:
        return []
    
    conditions = []
    for key in ("nombre", "radicado", "sede", "tipo_proceso", "demandante", "demandado"):
        v = metadata.get(key)
        if not v:
            continue
        match = _match_for_value(key, v)
        conditions.append(
            FieldCondition(key=key, match=match if match else MatchValue(value=v))
        )
    return conditions


# En el payload "nombre" la información se identifica por marcadores literales (no por los nombres
# de campo): RAD = radicado, DTE = demandante, DDO = demandado, TIPO = tipo_proceso.
# Esas palabras clave permiten dividir/identificar el texto en "nombre". Sede no aparece en "nombre"
# pero sigue siendo un filtro importante cuando el usuario la indica.
#
# Ej.: "nombre" = "10 039 RAD 19001-33-33-002-2014-00280-00 DTE myriam zapata puentes y otros DDO nacion
#       departamento del caqueta secretaria de educacion dptal TIPO nulidad y restablecimiento PAG 674"
NOMBRE_MARKERS = ("RAD", "DTE", "DDO", "TIPO")
_CAMPOS_EN_NOMBRE = ("radicado", "demandante", "demandado", "tipo_proceso")


def _build_nombre_search_terms(metadata: Dict[str, Optional[str]]) -> Optional[str]:
    """
    Construye una cadena de términos para buscar DENTRO del campo "nombre".
    Usa el valor completo de radicado, demandante, demandado y tipo_proceso (no segmentos ni truncado).
    En "nombre" el contenido se identifica por los marcadores RAD, DTE, DDO, TIPO.
    Sede no se incluye aquí porque no está en "nombre" (sede sigue usándose como filtro por campo).
    MatchText exige que todas las palabras estén presentes (substring match sin índice full-text).
    """
    parts = []
    r = metadata.get("radicado")
    if r:
        parts.append(r.strip())
    for key in ("demandante", "demandado"):
        v = metadata.get(key)
        if v:
            parts.append(v.strip())
    t = metadata.get("tipo_proceso")
    if t:
        parts.append(t.strip())
    if not parts:
        return None
    return " ".join(parts)


# Orden de prioridad. Sede no está en "nombre" (RAD/DTE/DDO/TIPO) pero sigue siendo filtro importante.
_FILTER_VARIANT_KEYS: List[List[str]] = [
    ["nombre", "radicado", "sede", "tipo_proceso", "demandante", "demandado"],  # 1) Todo
    ["radicado"],  # 2) Muy específico
    ["radicado", "demandante", "demandado", "tipo_proceso"],  # 3) Campos en "nombre" (RAD/DTE/DDO/TIPO)
    ["radicado", "sede", "tipo_proceso"],  # 4) Radicado + sede + tipo (sede importante como filtro)
    ["nombre"],  # 5) Expediente (coincidencia exacta)
    ["demandante", "demandado"],  # 6) Partes
    ["sede", "tipo_proceso"],  # 7) Sede + tipo
    ["radicado", "tipo_proceso"],  # 8) Radicado + tipo
    ["radicado"], ["nombre"], ["sede"], ["tipo_proceso"], ["demandante"], ["demandado"],  # 9) Un campo
]


def build_qdrant_filter_variants(
    metadata: Dict[str, Optional[str]],
) -> List[tuple]:
    """
    Genera variantes de filtro priorizadas. En "nombre" la información se identifica por
    los marcadores RAD, DTE, DDO, TIPO (radicado, demandante, demandado, tipo_proceso).
    Sede no está en "nombre" pero sigue siendo un filtro importante cuando el usuario la indica.
    
    Incluye una variante MatchText sobre "nombre" con radicado, demandante, demandado y
    tipo_proceso completos (búsqueda por substring/full-text dentro del campo "nombre").
    
    Returns:
        Lista de (Filter, descripción) para logging.
    """
    try:
        from qdrant_client.http.models import Filter, FieldCondition, MatchText
    except ImportError:
        return []
    
    conditions_by_key = {c.key: c for c in _conditions_for_metadata(metadata)}
    if not conditions_by_key:
        return []
    
    variants = []
    seen_keys = set()
    
    # Variante MatchText sobre "nombre": radicado + demandante + demandado + tipo_proceso completos.
    # En "nombre" el contenido se identifica por los marcadores RAD, DTE, DDO, TIPO. Sede no está en "nombre".
    nombre_terms = _build_nombre_search_terms(metadata)
    if nombre_terms and len(nombre_terms.strip()) >= 3:
        try:
            nombre_filter = Filter(
                must=[FieldCondition(key="nombre", match=MatchText(text=nombre_terms.strip()))]
            )
            variants.append((nombre_filter, "nombre(MatchText)"))
            seen_keys.add(("nombre_matchtext",))
            logger.debug(
                "🔍 Variante nombre(MatchText): términos '%s'",
                nombre_terms[:80] + ("..." if len(nombre_terms) > 80 else ""),
            )
        except Exception as e:
            logger.debug("🔍 MatchText en nombre no disponible: %s", e)
    
    for key_list in _FILTER_VARIANT_KEYS:
        combo = [conditions_by_key[k] for k in key_list if k in conditions_by_key]
        if not combo:
            continue
        key_names = sorted({c.key for c in combo})
        t = tuple(key_names)
        if t in seen_keys:
            continue
        seen_keys.add(t)
        desc = f"AND({','.join(key_names)})"
        variants.append((Filter(must=combo), desc))
    
    # Variante con should para demandante/demandado: must=[radicado, tipo_proceso] (campos en "nombre") + should=[demandante, demandado].
    # Sede no se usa en must porque no está en "nombre".
    if "demandante" in conditions_by_key and "demandado" in conditions_by_key:
        must_keys = ["radicado", "tipo_proceso"]
        must_conditions = [conditions_by_key[k] for k in must_keys if k in conditions_by_key]
        should_conditions = [conditions_by_key["demandante"], conditions_by_key["demandado"]]
        if must_conditions or should_conditions:
            desc = "AND(radicado,tipo) + OR(demandante,demandado)"
            t = ("should_variant", desc)
            if t not in seen_keys:
                seen_keys.add(t)
                variants.append(
                    (Filter(must=must_conditions, should=should_conditions), desc)
                )
    logger.info(f"🔍 Generadas {len(variants)} variantes de filtro priorizadas")
    return variants


def _normalize_caja_redundant_prefix(path: str) -> str:
    """
    Corrige el error de departamento en el JSON: "Caja_X/X <nombre>" -> "Caja_X/<nombre>".
    Elimina el prefijo redundante "X " (número de caja + espacio) tras "Caja_X/".
    X puede ser 1, 2, ..., n dígitos.
    
    Ej.: pdf/Caja_10/10 038 RAD... -> pdf/Caja_10/038 RAD...
    """
    # (Caja_(\d+)/)\2  => captura Caja_X/ y luego "X "; reemplazamos por Caja_X/
    return re.sub(r"(Caja_(\d+)/)\2 ", r"\1", path)


def convert_qdrant_pdf_link_to_hetzner_path(pdf_link: str) -> Optional[str]:
    """
    Convierte el pdf_link de Qdrant (formato gs://) al path de Hetzner Object Storage.
    Aplica normalización "Caja_X/X <nombre>" -> "Caja_X/<nombre>" por error en JSON maestro.
    
    Args:
        pdf_link: Path en formato gs://nextleap/condeabogados/expedientes/Caja_1/...pdf
        
    Returns:
        Path en formato pdf/Caja_1/...pdf o None si no se puede convertir
    """
    if not pdf_link:
        return None
    
    raw: Optional[str] = None
    
    # Extraer la parte después de 'expedientes/'
    if "expedientes/" in pdf_link:
        path_after_expedientes = pdf_link.split("expedientes/")[-1]
        raw = f"pdf/{path_after_expedientes}"
    elif pdf_link.startswith("pdf/"):
        raw = pdf_link
    else:
        logger.warning(f"⚠️  No se pudo convertir pdf_link: {pdf_link}")
        return None
    
    # Paso previo: normalizar "Caja_X/X <nombre>" -> "Caja_X/<nombre>" (error JSON maestro)
    normalized = _normalize_caja_redundant_prefix(raw)
    if normalized != raw:
        logger.debug(f"📄 Path normalizado (prefijo caja): {raw!r} -> {normalized!r}")
    
    return normalized


def generate_hetzner_signed_url(s3_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Genera una URL firmada (signed URL) para acceder a un objeto en Hetzner Object Storage.
    
    Args:
        s3_key: Clave del objeto en S3 (ej: pdf/Caja_1/documento.pdf)
        expiration: Tiempo de expiración en segundos (default: 1 hora)
        
    Returns:
        URL firmada o None si hay error
    """
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY]):
        logger.warning(f"⚠️  Hetzner S3 no configurado. No se pueden generar signed URLs.")
        logger.warning(f"    S3_ENDPOINT: {bool(S3_ENDPOINT)}, S3_BUCKET: {bool(S3_BUCKET)}, S3_ACCESS_KEY: {bool(S3_ACCESS_KEY)}, S3_SECRET_KEY: {bool(S3_SECRET_KEY)}")
        return None
    
    logger.info(f"🔗 Generando signed URL para: {s3_key} (bucket: {S3_BUCKET})")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # Configurar endpoint
        endpoint = S3_ENDPOINT
        if not endpoint.startswith(("http://", "https://")):
            endpoint = "https://" + endpoint
        
        # Crear cliente S3
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
        
        # Generar signed URL
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiration
        )
        
        logger.debug(f"✅ Signed URL generada para: {s3_key}")
        return signed_url
        
    except ClientError as e:
        logger.error(f"❌ Error al generar signed URL para {s3_key}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error inesperado al generar signed URL: {e}")
        return None


def _interpret_query_intent(question: str, llm_to_use=None) -> tuple[bool, str]:
    """
    Interpreta si la consulta del usuario requiere buscar en los documentos.
    Si es saludo, despedida, pregunta sin sentido u off-topic, no se hace retrieval.
    
    Returns:
        (should_search, message_if_no_search): si should_search es False, message_if_no_search
        es la respuesta amable a mostrar al usuario (sin fuentes documentales).
    """
    active_llm = llm_to_use if llm_to_use is not None else llm
    if not QUERY_INTENT_CHECK or not active_llm:
        return (True, "")
    question_stripped = (question or "").strip()
    if not question_stripped:
        return (False, "No has escrito ninguna pregunta. Escribe algo para buscar en los documentos.")
    try:
        prompt = (
            "Eres un clasificador. El asistente solo puede responder preguntas basándose en documentos subidos (expedientes, PDFs). "
            "Clasifica la siguiente entrada del usuario.\n\n"
            "Responde ÚNICAMENTE con un JSON válido, sin markdown ni texto extra, con estas claves:\n"
            '- "buscar_documentos": true si la consulta es una pregunta o petición que debe responderse buscando en los documentos (temas legales, expedientes, contenido de PDFs, etc.).\n'
            '- "buscar_documentos": false si es un saludo (hola, buenos días), despedida, pregunta sin sentido, chiste, tema que no requiere documentos (ej. hora, clima), o texto que no es una pregunta sobre el contenido documental.\n'
            '- "mensaje": si buscar_documentos es false, escribe aquí una respuesta corta, natural y amable al usuario (como si fueras un asistente conversando normalmente), sin mencionar explícitamente que "no requiere buscar en los documentos". Responde de forma directa y conversacional en español. Si buscar_documentos es true, déjalo vacío.\n\n'
            f'Entrada del usuario: "{question_stripped[:500]}"'
        )
        response = active_llm.complete(prompt)
        text = (response.text or "").strip()
        # Extraer JSON si viene envuelto en markdown (```json ... ```)
        if "```" in text:
            start = text.find("```")
            if "json" in text[:start + 10].lower():
                start = text.find("```", start) + 7
            else:
                start = text.find("```") + 3
            end = text.find("```", start)
            if end == -1:
                end = len(text)
            text = text[start:end].strip()
        data = json.loads(text)
        buscar = data.get("buscar_documentos", True)
        mensaje = (data.get("mensaje") or "").strip()
        if not buscar:
            msg = mensaje or "¿En qué puedo ayudarte? Puedo responder preguntas sobre los documentos subidos."
            logger.info(f"📋 Query intent: no document search. Returning message to user (no sources).")
            return (False, msg)
        return (True, "")
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        logger.debug(f"Query intent parse failed, proceeding with RAG: {e}")
        return (True, "")
    except Exception as e:
        logger.warning(f"Query intent check failed, proceeding with RAG: {e}")
        return (True, "")


def query(
    question: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    llm_provider: str = "gemini"
) -> Dict[str, Any]:
    """
    Query the RAG engine with a question.
    llm_provider: 'gemini' | 'ollama' - modelo a usar para generar la respuesta.
    
    Args:
        question: User's question
        conversation_history: Optional conversation history for context
        
    Returns:
        Dictionary with:
            - response: Generated response text
            - sources: List of source documents with metadata
    """
    global index  # Declare global at the beginning of the function
    if not query_engine:
        error_msg = (
            "Query engine not initialized. "
            f"LLM: {llm is not None}, "
            f"Embed Model: {embed_model is not None}, "
            f"Vector Store: {vector_store is not None}, "
            f"Index: {index is not None}"
        )
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Resolver LLM y query engine según proveedor
    active_llm = get_llm_for_provider(llm_provider)
    active_query_engine = get_query_engine_for_provider(llm_provider)
    
    if active_llm is None:
        raise ValueError(
            f"LLM no disponible para proveedor '{llm_provider}'. "
            "Gemini: verifica GEMINI_API_KEY. Ollama: verifica que ollama serve esté corriendo."
        )
    if active_query_engine is None:
        raise ValueError("Query engine no inicializado.")
    
    logger.info(f"   LLM Provider: {llm_provider}")
    
    # Interpretar si la consulta requiere buscar en documentos; si no, responder sin retrieval ni fuentes.
    should_search, no_search_message = _interpret_query_intent(question, llm_to_use=active_llm)
    if not should_search and no_search_message:
        logger.info("📋 Query does not require document search. Returning message without retrieval.")
        return {"response": no_search_message, "sources": []}
    
    try:
        import time
        query_start_time = time.time()
        
        # Instrucción para el proceso de pensamiento interno (chain of thought)
        # Específica para modelos R1 que tienen razonamiento interno
        thinking_instruction = (
            "Al responder, todo tu proceso de pensamiento interno (tu cadena de pensamiento) "
            "debe ser 100% en español. No utilices inglés ni mezcle idiomas en tu reflexión. "
            "Ejemplo de una cadena de pensamiento correcta: \"[razonamiento en español, sin palabras en inglés]\". "
            "¡Nunca utilices inglés en tu cadena de pensamiento! ¡Se trata de tu pensamiento interno, no del resultado!"
        )
        
        # Build query with conversation history if available
        if conversation_history:
            # Format history as context (optimized: reduced from 5 to 3 messages for faster processing)
            history_slice = conversation_history[-CONVERSATION_HISTORY_LIMIT:]
            history_context = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in history_slice
            ])
            enhanced_query = (
                f"{thinking_instruction}\n\n"
                f"Contexto de conversación anterior:\n{history_context}\n\n"
                f"Pregunta actual: {question}"
            )
            logger.debug(f"📝 Enhanced query with {len(history_slice)} history messages")
        else:
            enhanced_query = f"{thinking_instruction}\n\nPregunta: {question}"
        
        logger.info(f"🔍 Querying RAG engine...")
        logger.debug(f"   Question: {question[:100]}{'...' if len(question) > 100 else ''}")
        logger.debug(f"   History messages: {len(conversation_history) if conversation_history else 0}")
        logger.debug(f"   Similarity Top K: {SIMILARITY_TOP_K}")
        logger.debug(f"   Hybrid Search: {HYBRID_SEARCH_ENABLED} (alpha={HYBRID_ALPHA}, initial_k={HYBRID_INITIAL_TOP_K})")
        
        # Extract metadata and build filter variants only if metadata filtering is enabled.
        # USE_METADATA_FILTER=false evita 400 de Qdrant por índices faltantes (nombre, sede, etc.).
        extracted_metadata = extract_metadata_from_query(question) if USE_METADATA_FILTER else {}
        filter_variants = build_qdrant_filter_variants(extracted_metadata) if USE_METADATA_FILTER else []
        
        if not USE_METADATA_FILTER:
            logger.debug("📋 Filtro por metadata desactivado (USE_METADATA_FILTER=false). Solo búsqueda vectorial.")
        
        response = None
        max_attempts = 2
        GEMINI_429_WAIT = 12  # seconds, per API "Please retry in Xs"
        
        # Importar ResponseSynthesizer para Hybrid Search
        from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode
        
        for attempt in range(max_attempts):
            try:
                # ================================================================
                # HYBRID SEARCH: Vector retrieval + BM25 reranking
                # ================================================================
                if HYBRID_SEARCH_ENABLED and index:
                    # Paso 1: Recuperar más candidatos con búsqueda vectorial
                    initial_top_k = HYBRID_INITIAL_TOP_K
                    logger.info(f"🔀 Hybrid Search: Retrieving {initial_top_k} candidates for BM25 reranking...")
                    
                    hybrid_retriever = VectorIndexRetriever(
                        index=index,
                        similarity_top_k=initial_top_k,
                    )
                    
                    # Retrieve nodes (solo búsqueda vectorial, sin LLM)
                    candidate_nodes = hybrid_retriever.retrieve(enhanced_query)
                    logger.info(f"   Retrieved {len(candidate_nodes)} candidate nodes")
                    
                    # Paso 2: Aplicar BM25 reranking usando la pregunta original (sin thinking_instruction)
                    reranked_nodes = _bm25_rerank_nodes(question, candidate_nodes, top_k=SIMILARITY_TOP_K)
                    logger.info(f"   After BM25 reranking: {len(reranked_nodes)} nodes selected")
                    
                    # Paso 3: Generar respuesta con los nodos rerankeados
                    response_synthesizer = get_response_synthesizer(
                        llm=active_llm,
                        response_mode=ResponseMode.SIMPLE_SUMMARIZE,
                    )
                    response = response_synthesizer.synthesize(enhanced_query, nodes=reranked_nodes)
                    
                # ================================================================
                # METADATA FILTER SEARCH (sin hybrid)
                # ================================================================
                elif filter_variants and index:
                    for qdrant_filter, variant_desc in filter_variants:
                        try:
                            logger.info(f"🔍 Probando filtro: {variant_desc}")
                            filtered_retriever = VectorIndexRetriever(
                                index=index,
                                similarity_top_k=SIMILARITY_TOP_K,
                                vector_store_kwargs={"qdrant_filters": qdrant_filter}
                            )
                            filtered_query_engine = RetrieverQueryEngine.from_args(
                                retriever=filtered_retriever,
                                llm=active_llm,
                                response_mode=ResponseMode.SIMPLE_SUMMARIZE,
                            )
                            resp = filtered_query_engine.query(enhanced_query)
                            if hasattr(resp, 'source_nodes') and resp.source_nodes:
                                response = resp
                                logger.info(f"✅ Query con filtro exitoso: {variant_desc}. Sources: {len(resp.source_nodes)}")
                                break
                            logger.debug(f"   Sin resultados para {variant_desc}, probando siguiente...")
                        except Exception as e:
                            err_inner = str(e)
                            if "429" in err_inner and "RESOURCE_EXHAUSTED" in err_inner:
                                raise  # 429 → retry externo (no probar siguiente filtro)
                            logger.warning(f"⚠️  Error con filtro {variant_desc}: {str(e)}. Probando siguiente...")
                            continue
                    if response is None:
                        logger.warning("⚠️  Ninguna variante con filtro devolvió resultados. Fallback sin filtro.")
                        response = query_engine.query(enhanced_query)
                
                # ================================================================
                # STANDARD VECTOR SEARCH (fallback)
                # ================================================================
                else:
                    if not filter_variants:
                        logger.debug("📋 No se aplicó filtro (no se extrajo metadata relevante)")
                    response = response or active_query_engine.query(enhanced_query)
                break
            except Exception as e:
                err_str = str(e)
                is_429 = "429" in err_str and "RESOURCE_EXHAUSTED" in err_str
                if is_429 and attempt < max_attempts - 1:
                    logger.warning(f"⚠️ Gemini 429 (cuota). Esperando {GEMINI_429_WAIT}s antes de reintento ({attempt + 1}/{max_attempts})...")
                    time.sleep(GEMINI_429_WAIT)
                    continue
                if is_429:
                    raise Exception(
                        "Cuota de Gemini excedida. Reintenta en unos minutos o revisa tu plan en Google AI Studio: "
                        "https://ai.google.dev/gemini-api/docs/rate-limits"
                    ) from e
                raise
        
        query_duration = time.time() - query_start_time
        logger.info(f"⏱️  Query completed in {query_duration:.2f}s")
        
        # Extract response text
        response_text = str(response)
        
        # Check if LLM indicates no relevant information was found
        # Common phrases that indicate lack of relevant information
        no_info_indicators = [
            "no encontré información",
            "no tengo información",
            "no hay información",
            "no se encontró",
            "no está disponible",
            "no puedo responder",
            "no tengo datos",
            "no hay datos",
            "no encontré datos",
            "no está en los documentos",
            "no aparece en los documentos",
            "no se menciona",
            "no está presente",
            "no tengo conocimiento",
            "no puedo encontrar",
            "no hay evidencia",
            "no se proporciona",
            "no se especifica",
            "no se indica",
            "no está claro",
            "no está definido",
            "no está documentado"
        ]
        
        response_lower = response_text.lower()
        has_relevant_info = not any(indicator in response_lower for indicator in no_info_indicators)
        
        # Si el LLM indica que no hay información relevante, retornar inmediatamente sin procesar fuentes
        if not has_relevant_info:
            logger.info("⚠️  LLM response indicates no relevant information found. Skipping source processing and signed URL generation.")
            sources = []
        else:
            # Extract sources from response metadata ONLY if LLM found relevant info
            sources = []
            if hasattr(response, 'source_nodes') and response.source_nodes:
                for node in response.source_nodes:
                    source_info = {
                        "document_id": None,
                        "document_name": "Documento",
                        "snippet": "",
                        "score": None,
                        "page_number": None
                    }
                    
                    # Optimized: check node structure once
                    actual_node = node.node if hasattr(node, 'node') and node.node else node
                    
                    # Extract text and score from node
                    if hasattr(actual_node, 'text') and actual_node.text:
                        source_info["snippet"] = actual_node.text[:500]
                    elif hasattr(node, 'text') and node.text:
                        source_info["snippet"] = node.text[:500]
                    
                    # Extract score (similarity score from vector search)
                    node_score = None
                    if hasattr(node, 'score'):
                        node_score = node.score
                    elif hasattr(node, 'similarity'):
                        node_score = node.similarity
                    
                    source_info["score"] = node_score
                    
                    # Filter by similarity score threshold first (before extracting metadata and generating URLs)
                    if node_score is None or node_score < SIMILARITY_SCORE_THRESHOLD:
                        logger.debug(f"❌ Source filtered out by score: (score: {node_score if node_score is not None else 'N/A'}, threshold: {SIMILARITY_SCORE_THRESHOLD})")
                        continue
                    
                    # Extract metadata from node (optimized: single path)
                    metadata = {}
                    if hasattr(actual_node, 'metadata') and actual_node.metadata:
                        metadata = actual_node.metadata
                    elif hasattr(node, 'metadata') and node.metadata:
                        metadata = node.metadata
                    
                    if metadata:
                        # Log metadata keys for debugging
                        logger.info(f"📋 Metadata keys: {list(metadata.keys())}")
                        
                        # Extract document info (Qdrant payload uses 'nombre', 'page_num', etc.)
                        source_info["document_id"] = str(
                            metadata.get("document_id") or 
                            metadata.get("id") or 
                            metadata.get("exp_id") or 
                            ""
                        )
                        source_info["document_name"] = (
                            metadata.get("nombre") or  # Campo principal en Qdrant
                            metadata.get("document_name") or 
                            metadata.get("file_name") or 
                            metadata.get("filename") or 
                            "Documento"
                        )
                        source_info["page_number"] = (
                            metadata.get("page_num") or  # Campo en Qdrant
                            metadata.get("page_number")
                        )
                        
                        # Additional metadata from Qdrant payload
                        if metadata.get("radicado"):
                            source_info["radicado"] = metadata.get("radicado")
                        if metadata.get("demandante"):
                            source_info["demandante"] = metadata.get("demandante")
                        if metadata.get("demandado"):
                            source_info["demandado"] = metadata.get("demandado")
                        if metadata.get("tipo_proceso"):
                            source_info["tipo_proceso"] = metadata.get("tipo_proceso")
                        
                        # Extract and convert pdf_link from Qdrant format to Hetzner path
                        # Solo generar signed URLs DESPUÉS de confirmar has_relevant_info y score threshold
                        pdf_link_qdrant = metadata.get("pdf_link")
                        logger.info(f"📄 pdf_link from Qdrant: {pdf_link_qdrant}")
                        
                        if pdf_link_qdrant:
                            # Convert gs://nextleap/condeabogados/expedientes/... to pdf/...
                            hetzner_path = convert_qdrant_pdf_link_to_hetzner_path(pdf_link_qdrant)
                            logger.info(f"📄 Hetzner path converted: {hetzner_path}")
                            
                            if hetzner_path:
                                # Generate signed URL for Hetzner Object Storage
                                signed_url = generate_hetzner_signed_url(hetzner_path)
                                if signed_url:
                                    source_info["signed_url"] = signed_url
                                    source_info["pdf_path"] = hetzner_path
                                    logger.info(f"✅ PDF signed URL generada para: {source_info['document_name'][:50]}...")
                                else:
                                    logger.warning(f"⚠️  No se pudo generar signed URL para: {hetzner_path}")
                            else:
                                logger.warning(f"⚠️  No se pudo convertir pdf_link: {pdf_link_qdrant}")
                        else:
                            logger.warning(f"⚠️  No pdf_link found in metadata. Keys: {list(metadata.keys())}")
                    
                    # Source passed all filters: add to sources list
                    sources.append(source_info)
                    logger.debug(f"✅ Source included: {source_info.get('document_name', 'Unknown')} (score: {node_score:.3f})")
        
        logger.info(f"✅ Query completed successfully")
        logger.debug(f"   Response length: {len(response_text)} characters")
        logger.debug(f"   Sources found (after filtering): {len(sources)}")
        logger.debug(f"   Score threshold: {SIMILARITY_SCORE_THRESHOLD}")
        logger.debug(f"   Has relevant info (based on LLM response): {has_relevant_info}")
        
        # Log source details for debugging
        if sources:
            logger.debug("📚 Sources retrieved (after filtering):")
            for i, source in enumerate(sources[:3], 1):  # Log first 3 sources
                logger.debug(f"   {i}. {source.get('document_name', 'Unknown')} (score: {source.get('score', 'N/A')})")
        else:
            logger.debug("📚 No sources returned (filtered out due to low relevance or LLM indicating no info)")
        
        return {
            "response": response_text,
            "sources": sources
        }
        
    except Exception as e:
        logger.error(f"❌ Error querying LlamaIndex: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise Exception(f"Error al consultar el motor RAG: {str(e)}")


def get_query_engine_status() -> Dict[str, Any]:
    """
    Get the status of the query engine and its components.
    
    Returns:
        Dictionary with status information
    """
    global query_engine, query_engine_ollama, vector_store, llm, llm_gemini, llm_ollama, embed_model, index
    
    return {
        "query_engine_initialized": query_engine is not None,
        "vector_store_initialized": vector_store is not None,
        "llm_initialized": llm is not None,
        "embed_model_initialized": embed_model is not None,
        "qdrant_configured": bool(QDRANT_URL and QDRANT_API_KEY),
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL,
        "collection_name": QDRANT_COLLECTION,
        "qdrant_url_set": bool(QDRANT_URL),
        "qdrant_api_key_set": bool(QDRANT_API_KEY),
        # Performance settings
        "similarity_top_k": SIMILARITY_TOP_K,
        "similarity_score_threshold": SIMILARITY_SCORE_THRESHOLD,
        "use_metadata_filter": USE_METADATA_FILTER,
        "conversation_history_limit": CONVERSATION_HISTORY_LIMIT,
        "qdrant_timeout": QDRANT_TIMEOUT,
        "embed_model_name": os.getenv("EMBED_MODEL", "hiiamsid/sentence_similarity_spanish_es"),
        # Hybrid Search settings
        "hybrid_search_enabled": HYBRID_SEARCH_ENABLED,
        "hybrid_alpha": HYBRID_ALPHA,
        "hybrid_initial_top_k": HYBRID_INITIAL_TOP_K,
        # LLM Providers
        "ollama_available": llm_ollama is not None,
        "ollama_model": OLLAMA_MODEL,
        "gemini_available": llm_gemini is not None,
        "gemini_model": GEMINI_MODEL,
    }
