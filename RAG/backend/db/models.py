"""
Database models for the RAG application.
Roles: admin | user. Permissions granulares vía user_permissions.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


def _uuid_str():
    return str(uuid.uuid4())


ROLE_ADMIN = "admin"
ROLE_USER = "user"


class User(Base):
    """
    User model. role in (admin, user). is_active=False = soft block (reversible).
    """
    __tablename__ = "users"

    email = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    role = Column(String(32), nullable=False, default=ROLE_USER)

    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")


class UserPermission(Base):
    """
    Permisos granulares por usuario (ej. delete_own_agents, delete_own_history).
    Solo aplica a usuarios normales; admin tiene permisos maestros.
    """
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_email", "permission_key", name="uq_user_permission"),)

    id = Column(String(36), primary_key=True, default=_uuid_str)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True)
    permission_key = Column(String(64), nullable=False, index=True)

    user = relationship("User", back_populates="permissions")


class Agent(Base):
    """
    Agent (conversation) scoped per user. One user has many agents.
    """
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(256), nullable=False, default="Nueva conversación")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship(
        "AgentMessage",
        back_populates="agent",
        order_by="AgentMessage.created_at",
        cascade="all, delete-orphan",
    )


class AgentMessage(Base):
    """
    Mensajes del chat: user (pregunta) y assistant (respuesta + fuentes).
    Filas user: content = pregunta, user_email, request_id, session_id para auditoría.
    Filas assistant: content = respuesta del bot, sources = fuentes RAG (JSON).
    """
    __tablename__ = "agent_messages"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_email = Column(String, ForeignKey("users.email", ondelete="CASCADE"), nullable=True, index=True)  # null en assistant
    role = Column(String(32), nullable=False)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)  # fuentes RAG solo en assistant
    created_at = Column(DateTime, default=datetime.utcnow)
    request_id = Column(String(64), nullable=True, index=True)
    session_id = Column(String(64), nullable=True, index=True)

    agent = relationship("Agent", back_populates="messages")
