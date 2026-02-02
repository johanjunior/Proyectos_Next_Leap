"""
Rutas de administración: usuarios, permisos, auditoría.
Solo accesibles con rol admin.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.models import Agent, AgentMessage, User, UserPermission, ROLE_ADMIN, ROLE_USER
from backend.db.session import get_db
from backend.security.deps import get_current_user_resolved, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# --- Schemas ---

class UserOut(BaseModel):
    email: str
    name: Optional[str]
    picture: Optional[str]
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PermissionAdd(BaseModel):
    permission_key: str


class AuditEntryOut(BaseModel):
    id: str
    user_email: str
    agent_id: str
    user_input: str
    created_at: datetime
    request_id: Optional[str]
    session_id: Optional[str]


# --- Users ---

@router.get("/users", response_model=List[UserOut])
async def list_users(
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lista todos los usuarios. Solo admin."""
    users = db.query(User).order_by(User.email).all()
    return [UserOut.model_validate(u) for u in users]


@router.get("/users/{email}", response_model=UserOut)
async def get_user(
    email: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Detalle de un usuario. Solo admin."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    return UserOut.model_validate(user)


@router.patch("/users/{email}", response_model=UserOut)
async def update_user(
    email: str,
    body: UserUpdate,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Actualizar usuario (nombre, picture, role, is_active). Bloqueo = is_active False. Solo admin."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if body.name is not None:
        user.name = body.name
    if body.picture is not None:
        user.picture = body.picture
    if body.role is not None:
        if body.role not in (ROLE_ADMIN, ROLE_USER):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="role debe ser admin o user")
        user.role = body.role
    if body.is_active is not None:
        if email == admin.get("email") and body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No puedes desactivar tu propio usuario.",
            )
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/users/{email}/agents")
async def list_user_agents(
    email: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lista agentes de un usuario. Solo admin."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    agents = db.query(Agent).filter(Agent.user_email == email).order_by(Agent.updated_at.desc()).all()
    return [
        {"id": a.id, "name": a.name, "created_at": a.created_at, "updated_at": a.updated_at}
        for a in agents
    ]


# --- Permissions ---

@router.get("/users/{email}/permissions")
async def list_user_permissions(
    email: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Lista permisos de un usuario. Solo admin."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    perms = db.query(UserPermission).filter(UserPermission.user_email == email).all()
    return {"permissions": [p.permission_key for p in perms]}


@router.post("/users/{email}/permissions")
async def add_permission(
    email: str,
    body: PermissionAdd,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Asignar permiso a un usuario. Solo admin."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    key = (body.permission_key or "").strip()
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="permission_key requerido")
    existing = db.query(UserPermission).filter(
        UserPermission.user_email == email,
        UserPermission.permission_key == key,
    ).first()
    if existing:
        return {"message": "Permiso ya asignado", "user_email": email, "permission_key": key}
    perm = UserPermission(user_email=email, permission_key=key)
    db.add(perm)
    db.commit()
    return {"message": "Permiso asignado", "user_email": email, "permission_key": key}


@router.delete("/users/{email}/permissions/{permission_key}")
async def revoke_permission(
    email: str,
    permission_key: str,
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Revocar permiso. Solo admin."""
    perm = db.query(UserPermission).filter(
        UserPermission.user_email == email,
        UserPermission.permission_key == permission_key,
    ).first()
    if not perm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permiso no encontrado")
    db.delete(perm)
    db.commit()
    return {"message": "Permiso revocado"}


# --- Audit ---

@router.get("/audit/queries", response_model=List[AuditEntryOut])
async def audit_queries(
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
    user_email: Optional[str] = Query(None, description="Filtrar por usuario"),
    agent_id: Optional[str] = Query(None, description="Filtrar por agente"),
    since: Optional[datetime] = Query(None, description="Desde (iso)"),
    until: Optional[datetime] = Query(None, description="Hasta (iso)"),
    limit: int = Query(100, ge=1, le=500),
):
    """
    Historial de consultas (auditoría). Solo preguntas usuario; sin respuesta ni fuentes.
    Solo admin. Filtros opcionales: user_email, agent_id, since, until.
    """
    q = db.query(AgentMessage).filter(AgentMessage.role == "user")
    if user_email:
        q = q.filter(AgentMessage.user_email == user_email)
    if agent_id:
        q = q.filter(AgentMessage.agent_id == agent_id)
    if since:
        q = q.filter(AgentMessage.created_at >= since)
    if until:
        q = q.filter(AgentMessage.created_at <= until)
    rows = q.order_by(AgentMessage.created_at.desc()).limit(limit).all()
    return [
        AuditEntryOut(
            id=m.id,
            user_email=m.user_email,
            agent_id=m.agent_id,
            user_input=(m.content or "")[:2000],
            created_at=m.created_at,
            request_id=m.request_id,
            session_id=m.session_id,
        )
        for m in rows
    ]


@router.get("/stats")
async def get_stats(
    admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Estadísticas básicas. Solo admin."""
    total_users = db.query(User).count()
    total_agents = db.query(Agent).count()
    total_queries = db.query(AgentMessage).filter(AgentMessage.role == "user").count()
    return {
        "total_users": total_users,
        "total_agents": total_agents,
        "total_queries": total_queries,
    }
