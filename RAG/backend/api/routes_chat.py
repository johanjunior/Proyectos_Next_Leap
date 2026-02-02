"""
Chat routes for RAG queries.
Agents (conversations) are scoped per user (email). History persisted in DB.
"""
import asyncio
import logging
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.db.models import Agent, AgentMessage, ROLE_ADMIN
from backend.db.session import get_db
from backend.rag.llamaindex_engine import get_query_engine_status, query as rag_query
from backend.security.deps import (
    get_current_user,
    get_current_user_resolved,
    PERM_DELETE_OWN_AGENTS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


# --- Agents (historial por usuario) ---

class AgentCreate(BaseModel):
    """Request to create an agent."""
    name: Optional[str] = "Nueva conversación"


class AgentOut(BaseModel):
    """Agent list item."""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    """Message in agent history."""
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None


class AgentWithMessagesOut(BaseModel):
    """Agent with full message history."""
    id: str
    name: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageOut]


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Request model for chat query."""
    message: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Deprecated, use agent_id
    history: Optional[List[Dict]] = None
    session_id: Optional[str] = None  # Auditoría
    llm_provider: Optional[str] = "gemini"  # "gemini" | "ollama"


class Source(BaseModel):
    """Source document model."""
    document_id: str
    document_name: str
    page_number: Optional[int] = None
    snippet: str
    score: Optional[float] = None
    signed_url: Optional[str] = None
    pdf_path: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chat query."""
    response: str
    sources: List[Source]
    conversation_id: str  # Same as agent_id for compatibility
    agent_id: str
    agent_name: Optional[str] = None  # Nombre del agente (puede haberse actualizado en primer mensaje)


def _agent_for_user(db: Session, agent_id: str, user_email: str) -> Optional[Agent]:
    """Load agent by id; return None if not found or not owned by user."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent or agent.user_email != user_email:
        return None
    return agent


def _name_from_first_message(text: str, max_len: int = 32) -> str:
    """
    Deriva un nombre para el agente a partir del primer mensaje del usuario.
    Normaliza espacios, trunca y añade '…' si hace falta (títulos largos → puntos suspensivos).
    """
    s = (text or "").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s) <= max_len:
        return s if len(s) >= 3 else "Nueva conversación"
    return s[: max_len - 1].rstrip() + "…"


@router.get("/agents", response_model=List[AgentOut])
async def list_agents(
    current_user: dict = Depends(get_current_user_resolved),
    db: Session = Depends(get_db),
):
    """Lista agentes del usuario. Scoped by email."""
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email required")
    agents = db.query(Agent).filter(Agent.user_email == email).order_by(Agent.updated_at.desc()).all()
    return [AgentOut.model_validate(a) for a in agents]


@router.post("/agents", response_model=AgentOut)
async def create_agent(
    body: AgentCreate,
    current_user: dict = Depends(get_current_user_resolved),
    db: Session = Depends(get_db),
):
    """
    Create a new agent (conversation) for the current user.
    """
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email required")
    name = (body.name or "").strip() or "Nueva conversación"
    agent = Agent(user_email=email, name=name)
    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info(f"Agent created: {agent.id} for {email}")
    return AgentOut.model_validate(agent)


@router.get("/agents/{agent_id}", response_model=AgentWithMessagesOut)
async def get_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user_resolved),
    db: Session = Depends(get_db),
):
    """
    Agente e historial (solo preguntas usuario; no se almacenan respuestas ni fuentes).
    403 si no es del usuario.
    """
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email required")
    agent = _agent_for_user(db, agent_id, email)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado o sin acceso")
    messages = [
        MessageOut(role=m.role, content=m.content, sources=getattr(m, "sources", None))
        for m in agent.messages
    ]
    return AgentWithMessagesOut(
        id=agent.id,
        name=agent.name,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        messages=messages,
    )


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    current_user: dict = Depends(get_current_user_resolved),
    db: Session = Depends(get_db),
):
    """
    Elimina un agente (y sus mensajes). Admin siempre; usuario solo con permiso
    delete_own_agents y si es su agente. 403 si no tiene permiso.
    """
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email required")
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado")
    is_owner = agent.user_email == email
    is_admin = current_user.get("role") == ROLE_ADMIN
    has_perm = PERM_DELETE_OWN_AGENTS in (current_user.get("permissions") or [])
    if not (is_admin or (has_perm and is_owner)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permiso para eliminar este agente.",
        )
    db.delete(agent)
    db.commit()
    logger.info(f"Agent deleted: {agent_id} by {email}")


@router.post("/query", response_model=ChatResponse)
async def chat_query(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user_resolved),
    db: Session = Depends(get_db),
):
    """
    Procesa una consulta RAG. Requiere agent_id.
    Persiste pregunta (user) y respuesta + fuentes (assistant) para mostrar historial al cambiar de agente.
    """
    try:
        email = current_user.get("email")
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User email required")

        agent_id = request.agent_id or request.conversation_id
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="agent_id es obligatorio. Crea un agente con POST /chat/agents o selecciona uno existente.",
            )

        agent = _agent_for_user(db, agent_id, email)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agente no encontrado o sin acceso")

        # Historial solo preguntas usuario (no se almacenan respuestas)
        messages = [{"role": m.role, "content": m.content} for m in agent.messages]
        messages.append({"role": "user", "content": request.message})
        history_for_rag = messages[:-1]

        logger.info("=" * 70)
        logger.info("🔍 Processing RAG Query")
        logger.info("=" * 70)
        logger.info(f"   User: {email}")
        logger.info(f"   Agent ID: {agent_id}")
        logger.info(f"   Message: {request.message[:100]}{'...' if len(request.message) > 100 else ''}")
        logger.info(f"   History messages: {len(history_for_rag)}")

        rag_status = get_query_engine_status()
        if not rag_status.get("query_engine_initialized"):
            raise ValueError(
                "Query engine no inicializado. "
                f"Qdrant: {rag_status.get('qdrant_configured')}, Gemini: {rag_status.get('gemini_configured')}, "
                f"Vector Store: {rag_status.get('vector_store_initialized')}, LLM: {rag_status.get('llm_initialized')}, "
                f"Embed Model: {rag_status.get('embed_model_initialized')}"
            )

        import time
        query_start = time.time()
        llm_provider = (request.llm_provider or "gemini").lower().strip()
        rag_result = await asyncio.to_thread(
            rag_query,
            question=request.message,
            conversation_history=history_for_rag,
            llm_provider=llm_provider,
        )
        query_duration = time.time() - query_start
        logger.info(f"⏱️  Total query time: {query_duration:.2f}s")

        response_text = rag_result["response"]
        sources_data = rag_result["sources"]

        sources_list = [
            Source(
                document_id=str(s.get("document_id", "")),
                document_name=s.get("document_name", "Documento"),
                page_number=s.get("page_number"),
                snippet=s.get("snippet", ""),
                score=s.get("score"),
                signed_url=s.get("signed_url"),
                pdf_path=s.get("pdf_path"),
            )
            for s in sources_data
        ]

        # Persistir pregunta (auditoría) y respuesta (historial en UI).
        request_id = str(uuid.uuid4())
        um = AgentMessage(
            agent_id=agent_id,
            user_email=email,
            role="user",
            content=request.message,
            request_id=request_id,
            session_id=request.session_id,
        )
        db.add(um)
        sources_dicts = [
            {
                "document_id": str(s.get("document_id", "")),
                "document_name": s.get("document_name", "Documento"),
                "page_number": s.get("page_number"),
                "snippet": s.get("snippet", ""),
                "score": s.get("score"),
                "signed_url": s.get("signed_url"),
                "pdf_path": s.get("pdf_path"),
            }
            for s in sources_data
        ]
        am = AgentMessage(
            agent_id=agent_id,
            user_email=None,
            role="assistant",
            content=response_text,
            sources=sources_dicts,
        )
        db.add(am)

        agent_name = agent.name
        if len(agent.messages) == 0:
            new_name = _name_from_first_message(request.message)
            db.execute(
                update(Agent)
                .where(Agent.id == agent_id)
                .values(name=new_name, updated_at=datetime.utcnow())
            )
            agent_name = new_name
            logger.info(f"Agent name updated from first message: {new_name[:50]}...")
        else:
            db.execute(update(Agent).where(Agent.id == agent_id).values(updated_at=datetime.utcnow()))

        db.commit()

        return ChatResponse(
            response=response_text,
            sources=sources_list,
            conversation_id=agent_id,
            agent_id=agent_id,
            agent_name=agent_name,
        )

    except HTTPException:
        raise
    except ValueError as e:
        import traceback
        logger.error(f"❌ ValueError in chat_query: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        import traceback
        logger.error(f"❌ Exception in chat_query: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al procesar la consulta: {str(e)}")


@router.get("/status")
async def get_rag_status(
    current_user: dict = Depends(get_current_user_resolved),
):
    """Estado del motor RAG. Requiere usuario no bloqueado."""
    return get_query_engine_status()
