#!/usr/bin/env python3
"""
Crea índices de payload (keyword) en la colección de Qdrant para habilitar
filtrado por metadata (nombre, sede, radicado, tipo_proceso, demandante, demandado).

Sin estos índices, Qdrant devuelve 400: "Index required but not found for X of type [keyword]".

Ejecutar una vez (o tras crear la colección):
  conda activate rag-mvp
  cd /ruta/al/proyecto/RAG
  python backend/scripts/create_qdrant_payload_indexes.py
  # Si ocr_to_qdrant usa otra colección:
  python backend/scripts/create_qdrant_payload_indexes.py --collection expedientes_ocr

Requiere .env con QDRANT_URL, QDRANT_API_KEY. Usa QDRANT_COLLECTION o --collection.
"""
from pathlib import Path
import argparse
import os
import sys

# Project root = RAG/
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))
os.chdir(_project_root)

from dotenv import load_dotenv
load_dotenv(dotenv_path=_project_root / ".env", override=True)

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION", "expedientes_ocr")

# Campos del payload usados en filtros por metadata (MatchValue → keyword)
INDEX_FIELDS = [
    "doc_key",      # Requerido para verificación de existencia y deduplicación
    "source_path",  # Requerido para compatibilidad con documentos antiguos
    "caja_key",
    "nombre",
    "sede",
    "radicado",
    "tipo_proceso",
    "demandante",
    "demandado",
    "exp_id",
    "page_num"
]


def main():
    parser = argparse.ArgumentParser(description="Crear índices de payload en Qdrant")
    parser.add_argument("--collection", "-c", default=DEFAULT_COLLECTION,
                        help=f"Nombre de la colección (default: {DEFAULT_COLLECTION})")
    args = parser.parse_args()
    collection = args.collection

    if not QDRANT_URL or not QDRANT_API_KEY:
        print("❌ Configura QDRANT_URL y QDRANT_API_KEY en .env")
        sys.exit(1)

    from qdrant_client import QdrantClient

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print(f"✅ Conectado a Qdrant. Colección: {collection}")

    for field in INDEX_FIELDS:
        try:
            client.create_payload_index(
                collection_name=collection,
                field_name=field,
                field_schema="keyword",
            )
            print(f"   ✅ Índice creado: {field}")
        except Exception as e:
            if "already exists" in str(e).lower() or "already exist" in str(e).lower():
                print(f"   ⏭️  {field} (ya existe)")
            else:
                print(f"   ❌ {field}: {e}")

    print("✅ Hecho. Puedes activar filtrado con USE_METADATA_FILTER=true en .env")


if __name__ == "__main__":
    main()
