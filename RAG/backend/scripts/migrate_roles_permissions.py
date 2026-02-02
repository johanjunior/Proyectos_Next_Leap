#!/usr/bin/env python3
"""
Migración: roles, permisos, agent_messages solo auditoría.

- Añade User.role (admin|user).
- Crea user_permissions.
- Añade agent_messages.user_email, request_id, session_id.
- Backfill user_email desde agents.
- Elimina filas role='assistant' y deja de usar 'sources'.

Ejecutar una vez antes de usar el nuevo código:
  python -m backend.scripts.migrate_roles_permissions

Requiere DATABASE_URL en .env (por defecto sqlite:///./rag_app.db).
"""
from pathlib import Path
import os
import sys

_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

from dotenv import load_dotenv
load_dotenv(_project_root / ".env", override=True)

from sqlalchemy import text
from backend.db.session import engine


def _has_column(conn, table: str, column: str) -> bool:
    r = conn.execute(text(f"PRAGMA table_info({table})"))
    return any(row[1] == column for row in r.fetchall())


def _has_table(conn, table: str) -> bool:
    r = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table})
    return r.fetchone() is not None


def run():
    with engine.connect() as conn:
        with conn.begin():
            # 1) User.role
            if not _has_column(conn, "users", "role"):
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(32) NOT NULL DEFAULT 'user'"))
                print("   + users.role")
            else:
                print("   users.role ya existe")

            # 2) user_permissions
            if not _has_table(conn, "user_permissions"):
                conn.execute(text("""
                    CREATE TABLE user_permissions (
                        id VARCHAR(36) PRIMARY KEY,
                        user_email VARCHAR NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                        permission_key VARCHAR(64) NOT NULL,
                        UNIQUE(user_email, permission_key)
                    )
                """))
                conn.execute(text("CREATE INDEX ix_user_permissions_user_email ON user_permissions(user_email)"))
                conn.execute(text("CREATE INDEX ix_user_permissions_permission_key ON user_permissions(permission_key)"))
                print("   + user_permissions")
            else:
                print("   user_permissions ya existe")

            # 3) agent_messages: user_email, request_id, session_id
            for col, typ in [
                ("user_email", "VARCHAR REFERENCES users(email) ON DELETE CASCADE"),
                ("request_id", "VARCHAR(64)"),
                ("session_id", "VARCHAR(64)"),
            ]:
                if not _has_column(conn, "agent_messages", col):
                    conn.execute(text(f"ALTER TABLE agent_messages ADD COLUMN {col} {typ}"))
                    print(f"   + agent_messages.{col}")

            # Backfill user_email desde agents
            conn.execute(text("""
                UPDATE agent_messages SET user_email = (
                    SELECT user_email FROM agents WHERE agents.id = agent_messages.agent_id
                ) WHERE user_email IS NULL OR user_email = ''
            """))
            print("   backfill user_email")

            # 4) Eliminar filas assistant
            conn.execute(text("DELETE FROM agent_messages WHERE role = 'assistant'"))
            print("   filas assistant eliminadas")

    print("Migración lista.")

if __name__ == "__main__":
    run()
