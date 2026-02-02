#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import uuid
import time
import argparse
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from openai import OpenAI


# ----------------------------
# 1) Ordenar páginas pag_<n>
# ----------------------------
PAGE_RE = re.compile(r"^pag_(\d+)$", re.IGNORECASE)

def sorted_pages(paginas: Dict[str, Any]) -> List[Tuple[int, str, Any]]:
    """
    Devuelve lista ordenada: [(page_num, page_key, page_obj), ...]
    Ordena por page_num extraído de keys tipo 'pag_10'.
    Keys no reconocidas quedan al final.
    """
    ordered: List[Tuple[int, str, Any]] = []
    unknown: List[Tuple[str, Any]] = []

    for k, v in (paginas or {}).items():
        if not isinstance(k, str):
            continue
        m = PAGE_RE.match(k.strip())
        if m:
            ordered.append((int(m.group(1)), k, v))
        else:
            unknown.append((k, v))

    ordered.sort(key=lambda x: x[0])

    # desconocidas al final
    base = (ordered[-1][0] if ordered else 0) + 1
    for i, (k, v) in enumerate(unknown):
        ordered.append((base + i, k, v))

    return ordered


# ----------------------------
# 2) Utilidades de texto
# ----------------------------
def normalize_whitespace(s: str) -> str:
    s = s.replace("\u0000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> List[str]:
    """
    Chunking simple por caracteres con solape.
    """
    text = text.strip()
    if not text:
        return []

    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    chunks: List[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(n, start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == n:
            break
        start = max(0, end - overlap)

    return chunks


def safe_json_load(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error leyendo JSON {path}: {e}")
        return None


# ----------------------------
# 3) Qdrant helpers
# ----------------------------
def ensure_collection(
    client_q: QdrantClient,
    collection: str,
    vector_size: int,
    distance: Distance = Distance.COSINE,
) -> None:
    """
    Crea la colección si no existe. Si existe, no toca su schema.
    """
    existing = {c.name for c in client_q.get_collections().collections}
    if collection in existing:
        return

    client_q.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=vector_size, distance=distance),
    )
    print(f"✅ Colección creada: {collection} (size={vector_size}, distance={distance})")


def wipe_collection(client_q: QdrantClient, collection: str) -> None:
    """
    Borra todos los puntos de la colección (sin borrar la colección).
    """
    client_q.delete(
        collection_name=collection,
        points_selector=Filter(must=[]),  # filtro vacío => match all
    )
    print(f"🧹 Colección '{collection}' limpiada (todos los puntos eliminados)")


# ----------------------------
# 4) Extracción OCR -> texto
# ----------------------------
def ocr_json_to_pages_text(ocr_doc: Dict[str, Any]) -> List[Tuple[int, str]]:
    """
    Retorna lista de (page_num, texto) ordenado.
    """
    paginas = ocr_doc.get("paginas") or {}
    out: List[Tuple[int, str]] = []

    for page_num, page_key, page_obj in sorted_pages(paginas):
        if not isinstance(page_obj, dict):
            continue
        txt = page_obj.get("texto", "")
        if not isinstance(txt, str):
            continue
        txt = normalize_whitespace(txt)
        if txt:
            out.append((page_num, txt))

    return out


def derive_meta_from_doc(ocr_doc: Dict[str, Any], json_path: Path) -> Dict[str, Any]:
    """
    Toma metadata del JSON OCR + fallback del path.
    """
    md = ocr_doc.get("metadata") or {}
    if not isinstance(md, dict):
        md = {}

    # Caja desde metadata o desde folder
    caja_key = md.get("caja_key")
    if not caja_key:
        # ejemplo: .../OCR/Caja_10/<archivo>.json
        for p in json_path.parts[::-1]:
            if isinstance(p, str) and p.lower().startswith("caja_"):
                caja_key = p
                break

    exp_id = md.get("exp_id") or md.get("id")
    nombre = md.get("nombre") or json_path.stem
    radicado = md.get("radicado")

    sede = md.get("sede")
    tipo_proceso = md.get("tipo_proceso")
    demandante = md.get("demandante")
    demandado = md.get("demandado")

    link_pdf = ocr_doc.get("link")

    return {
        "caja_key": caja_key,
        "exp_id": exp_id,
        "nombre": nombre,
        "radicado": radicado,
        "sede": sede,
        "tipo_proceso": tipo_proceso,
        "demandante": demandante,
        "demandado": demandado,
        "pdf_link": link_pdf,
    }


# ----------------------------
# 5) Main ingest
# ----------------------------
def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Ingest OCR JSONs to Qdrant")
    parser.add_argument("--ocr-dir", default="data/OCR", help="Directorio base OCR (default: data/OCR)")
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "expedientes_ocr"),
                        help="Nombre colección Qdrant")
    parser.add_argument("--wipe", action="store_true", help="Eliminar todos los puntos antes de ingerir")
    parser.add_argument("--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", "1200")))
    parser.add_argument("--overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", "150")))
    parser.add_argument("--batch-embed", type=int, default=int(os.getenv("EMBED_BATCH", "64")))
    parser.add_argument("--batch-upsert", type=int, default=int(os.getenv("UPSERT_BATCH", "128")))
    args = parser.parse_args()

    # ---- Clientes
    qdrant_url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_HOST") or "http://localhost:6333"
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection = args.collection

    client_q = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise RuntimeError("Falta OPENAI_API_KEY en .env")

    client_oai = OpenAI(api_key=openai_key)
    embed_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

    # ---- Detectar tamaño del embedding (sin adivinar)
    probe = client_oai.embeddings.create(model=embed_model, input=["probe"])
    vector_size = len(probe.data[0].embedding)

    ensure_collection(client_q, collection, vector_size=vector_size)

    if args.wipe:
        wipe_collection(client_q, collection)

    # ---- Encontrar archivos OCR
    ocr_dir = Path(args.ocr_dir)
    if not ocr_dir.exists():
        raise RuntimeError(f"No existe el directorio OCR: {ocr_dir.resolve()}")

    # Ignoramos el maestro entrega_ocr_*.json si está en raíz
    all_json = sorted([p for p in ocr_dir.rglob("*.json") if p.is_file()])
    files = []
    for p in all_json:
        # si es un "entrega_ocr_*.json" en raíz OCR, saltarlo
        if p.parent == ocr_dir and p.name.lower().startswith("entrega_ocr_"):
            continue
        files.append(p)

    print(f"📦 Archivos OCR encontrados: {len(files)}")

    # ---- Pipeline: construir textos + embed + upsert
    chunk_size = args.chunk_size
    overlap = args.overlap
    batch_embed = args.batch_embed
    batch_upsert = args.batch_upsert

    to_embed: List[str] = []
    to_payloads: List[Dict[str, Any]] = []

    total_points = 0
    t0 = time.time()

    def flush_embed_and_upsert() -> int:
        nonlocal to_embed, to_payloads, total_points
        if not to_embed:
            return 0

        emb = client_oai.embeddings.create(model=embed_model, input=to_embed)
        vectors = [e.embedding for e in emb.data]

        points: List[PointStruct] = []
        for text, payload, vec in zip(to_embed, to_payloads, vectors):
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),  # ✅ UUID válido (corrige tu error)
                    vector=vec,
                    payload={**payload, "text": text},
                )
            )

        # Upsert en batches para no mandar payload enorme
        for i in range(0, len(points), batch_upsert):
            batch_points = points[i:i + batch_upsert]
            client_q.upsert(collection_name=collection, points=batch_points)
            total_points += len(batch_points)

        done = len(points)
        to_embed = []
        to_payloads = []
        return done

    for idx, json_path in enumerate(files, start=1):
        doc = safe_json_load(json_path)
        if not doc:
            continue

        meta = derive_meta_from_doc(doc, json_path)
        pages = ocr_json_to_pages_text(doc)

        if not pages:
            continue

        # Estrategia: chunk por página (mejor trazabilidad)
        # Si querés chunk global del documento, se puede cambiar.
        for page_num, page_text in pages:
            chunks = chunk_text(page_text, chunk_size=chunk_size, overlap=overlap)
            if not chunks:
                continue

            for ci, chunk in enumerate(chunks):
                payload = {
                    "doc_type": "ocr",
                    "source_path": str(json_path),
                    "caja_key": meta.get("caja_key"),
                    "exp_id": meta.get("exp_id"),
                    "nombre": meta.get("nombre"),
                    "radicado": meta.get("radicado"),
                    "sede": meta.get("sede"),
                    "tipo_proceso": meta.get("tipo_proceso"),
                    "demandante": meta.get("demandante"),
                    "demandado": meta.get("demandado"),
                    "pdf_link": meta.get("pdf_link"),
                    "page_num": page_num,          # ✅ entero para ordenar bien luego
                    "chunk_in_page": ci,           # chunk dentro de la página
                }

                to_embed.append(chunk)
                to_payloads.append(payload)

                # Flush cuando llegue al batch de embeddings
                if len(to_embed) >= batch_embed:
                    done = flush_embed_and_upsert()
                    print(f"✅ Upsert {done} puntos (archivo {idx}/{len(files)})")

    # Flush final
    done_final = flush_embed_and_upsert()
    if done_final:
        print(f"✅ Upsert final {done_final} puntos")

    dt = time.time() - t0
    print(f"🏁 Ingesta finalizada. Puntos totales: {total_points}. Tiempo: {dt:.1f}s")


if __name__ == "__main__":
    main()

