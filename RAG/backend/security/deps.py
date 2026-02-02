"""
Dependencies for authentication and authorization.
Roles: admin | user. Permisos granulares vía user_permissions.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.db.models import User, UserPermission, ROLE_ADMIN
from backend.db.session import get_db
from backend.security.jwt import decode_access_token

security = HTTPBearer()

# Permisos granulares (solo usuarios normales; admin tiene todos)
PERM_DELETE_OWN_AGENTS = "delete_own_agents"
PERM_DELETE_OWN_HISTORY = "delete_own_history"


def _user_to_dict(u: User, permissions: List[str]) -> dict:
    return {
        "email": u.email,
        "name": u.name,
        "picture": u.picture,
        "role": u.role,
        "is_active": u.is_active,
        "permissions": permissions,
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Usuario desde JWT (sin DB). No comprueba is_active ni role.
    Usar get_current_user_resolved para autorización.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    user_email: Optional[str] = payload.get("sub")
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "email": user_email,
        "name": payload.get("name"),
        "picture": payload.get("picture"),
    }


async def get_current_user_resolved(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> dict:
    """
    Usuario desde JWT + DB. Incluye role, is_active, permissions.
    Rechaza si is_active=False (bloqueado).
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    user_email: Optional[str] = payload.get("sub")
    if user_email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario bloqueado o desactivado.",
        )
    perms = [p.permission_key for p in user.permissions]
    return _user_to_dict(user, perms)


def require_admin(user: dict = Depends(get_current_user_resolved)) -> dict:
    """Exige rol admin. 403 si no."""
    if user.get("role") != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol administrador.")
    return user


def require_permission(permission_key: str):
    """Devuelve un dep que exige admin o el permiso granular."""

    async def _dep(user: dict = Depends(get_current_user_resolved)) -> dict:
        if user.get("role") == ROLE_ADMIN:
            return user
        if permission_key in (user.get("permissions") or []):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permiso: {permission_key}",
        )

    return _dep
