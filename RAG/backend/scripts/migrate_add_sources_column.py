#!/usr/bin/env python3
"""
Añade la columna sources a agent_messages si no existe (para guardar respuestas del bot y fuentes).
Ejecutar una vez si la tabla ya existía sin esta columna:
  python -m backend.scripts.migrate_add_sources_column
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


def run():
    with engine.connect() as conn:
        with conn.begin():
            if not _has_column(conn, "agent_messages", "sources"):
                conn.execute(text("ALTER TABLE agent_messages ADD COLUMN sources TEXT"))
                print("   + agent_messages.sources")
            else:
                print("   agent_messages.sources ya existe")
    print("Migración lista.")


if __name__ == "__main__":
    run()
