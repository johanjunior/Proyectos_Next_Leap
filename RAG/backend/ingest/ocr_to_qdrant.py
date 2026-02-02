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
    FilterSelector,
)
from sentence_transformers import SentenceTransformer


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
# 2.5) Debug
# ----------------------------
_DEBUG = False

def _dbg(msg: str) -> None:
    if _DEBUG:
        print(f"   [DEBUG] {msg}")


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


def document_exists_in_qdrant(
    client_q: QdrantClient,
    collection: str,
    doc_key: str,
    source_path: Optional[str] = None,
) -> bool:
    """
    Comprueba si ya existe al menos un punto en Qdrant para este documento.
    - doc_key: identificador nuevo (ruta relativa Caja_X/archivo.json).
    - source_path: ruta completa usada en documentos antiguos (str(json_path)).
    Comprueba ambos para detectar documentos subidos antes o después del campo doc_key.
    """
    conditions = [FieldCondition(key="doc_key", match=MatchValue(value=doc_key))]
    if source_path:
        conditions.append(FieldCondition(key="source_path", match=MatchValue(value=source_path)))
    _dbg(f"document_exists: doc_key={doc_key!r} source_path={repr(source_path)[:100]}")
    try:
        result, _ = client_q.scroll(
            collection_name=collection,
            scroll_filter=Filter(should=conditions),
            limit=1,
        )
        exists = len(result) > 0
        _dbg(f"document_exists: scroll retornó {len(result)} punto(s) → exists={exists}")
        return exists
    except Exception as e:
        _dbg(f"document_exists: EXCEPCIÓN {e}")
        return False


def get_max_page_num_for_doc_key(
    client_q: QdrantClient,
    collection: str,
    doc_key: str,
    source_path: Optional[str] = None,
) -> Optional[int]:
    """
    Obtiene el máximo page_num de los puntos con doc_key (o source_path) dado en Qdrant.
    Retorna None si no existe ningún punto. Comprueba ambos para formato nuevo y antiguo.
    """
    conditions = [FieldCondition(key="doc_key", match=MatchValue(value=doc_key))]
    if source_path:
        conditions.append(FieldCondition(key="source_path", match=MatchValue(value=source_path)))
    _dbg(f"get_max_page_num: buscando doc_key={doc_key!r}")
    try:
        result, _ = client_q.scroll(
            collection_name=collection,
            scroll_filter=Filter(should=conditions),
            limit=10000,
        )
        _dbg(f"get_max_page_num: scroll retornó {len(result)} punto(s)")
        if not result:
            return None
        page_nums = [
            p.payload.get("page_num")
            for p in result
            if p.payload and p.payload.get("page_num") is not None
        ]
        max_page = max(page_nums) if page_nums else None
        _dbg(f"get_max_page_num: page_nums sample={page_nums[:5]}{'...' if len(page_nums) > 5 else ''} → max={max_page}")
        return max_page
    except Exception as e:
        _dbg(f"get_max_page_num: EXCEPCIÓN {e}")
        return None


def delete_points_by_doc_key(
    client_q: QdrantClient,
    collection: str,
    doc_key: str,
    source_path: Optional[str] = None,
) -> int:
    """
    Elimina todos los puntos cuyo payload tiene doc_key o source_path.
    Usa OR para eliminar tanto formato nuevo (doc_key) como antiguo (source_path).
    Retorna 1 si éxito, 0 si hubo error.
    """
    conditions = [FieldCondition(key="doc_key", match=MatchValue(value=doc_key))]
    if source_path:
        conditions.append(FieldCondition(key="source_path", match=MatchValue(value=source_path)))
    _dbg(f"delete_points: eliminando doc_key={doc_key!r} (filter: doc_key OR source_path)")
    try:
        client_q.delete(
            collection_name=collection,
            points_selector=FilterSelector(
                filter=Filter(should=conditions)
            ),
        )
        _dbg(f"delete_points: eliminación OK")
        return 1
    except Exception as e:
        print(f"    ⚠️  Error al eliminar puntos para {doc_key}: {e}")
        _dbg(f"delete_points: EXCEPCIÓN {e}")
        return 0


def get_original_num_pages(doc: Dict[str, Any], pages_from_ocr: List[Tuple[int, str]]) -> int:
    """
    Obtiene el número de páginas del documento.
    Prioridad: metadata.paginas > contar páginas extraídas del OCR.
    """
    md = doc.get("metadata") or {}
    if isinstance(md, dict):
        paginas = md.get("paginas")
        if paginas is not None and isinstance(paginas, (int, float)):
            _dbg(f"get_original_num_pages: metadata.paginas={paginas}")
            return int(paginas)
    # Fallback: contar páginas extraídas
    n = len(pages_from_ocr) if pages_from_ocr else 0
    _dbg(f"get_original_num_pages: fallback len(pages_from_ocr)={n}")
    return n


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
    # Cargar .env desde la raíz del proyecto
    project_root = Path(__file__).resolve().parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    print(f"📂 Cargando .env desde: {env_path}")
    print(f"📂 .env existe: {env_path.exists()}")

    parser = argparse.ArgumentParser(description="Ingest OCR JSONs to Qdrant")
    parser.add_argument("--ocr-dir", default="data/OCR", help="Directorio base OCR (default: data/OCR)")
    parser.add_argument("--collection", default=os.getenv("QDRANT_COLLECTION", "expedientes_ocr"),
                        help="Nombre colección Qdrant")
    parser.add_argument("--wipe", action="store_true", help="Eliminar todos los puntos antes de ingerir")
    parser.add_argument("--no-skip-existing", action="store_true", dest="force",
                        help="Re-procesar documentos ya subidos (por defecto se omiten)")
    parser.add_argument("--chunk-size", type=int, default=int(os.getenv("CHUNK_SIZE", "1200")))
    parser.add_argument("--overlap", type=int, default=int(os.getenv("CHUNK_OVERLAP", "150")))
    parser.add_argument("--batch-embed", type=int, default=int(os.getenv("EMBED_BATCH", "64")))
    parser.add_argument("--batch-upsert", type=int, default=int(os.getenv("UPSERT_BATCH", "128")))
    parser.add_argument("--debug", "-d", action="store_true", help="Mostrar mensajes de depuración")
    args = parser.parse_args()

    global _DEBUG
    _DEBUG = args.debug
    if _DEBUG:
        print("🔧 Modo DEBUG activado")

    # ---- Clientes
    qdrant_url = os.getenv("QDRANT_URL") or os.getenv("QDRANT_HOST") or "http://localhost:6333"
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection = args.collection

    client_q = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    # ---- Inicializar modelo de sentence-transformers
    embed_model_name = os.getenv("EMBED_MODEL", "hiiamsid/sentence_similarity_spanish_es")
    print(f"🤖 Cargando modelo de embedding: {embed_model_name}")
    print("   (Esto puede tomar unos segundos la primera vez que se descarga el modelo)")
    
    try:
        embed_model = SentenceTransformer(embed_model_name)
        # hiiamsid/sentence_similarity_spanish_es (especializado en español)
        vector_size = embed_model.get_sentence_embedding_dimension()
        print(f"✅ Modelo cargado. Dimensiones del vector: {vector_size}")
    except Exception as e:
        raise RuntimeError(f"Error al cargar el modelo de embedding '{embed_model_name}': {e}")

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

    # ---- Limitar a las primeras 5 carpetas
    # Agrupar archivos por carpeta (Caja_X)
    files_by_folder: Dict[str, List[Path]] = {}
    for p in files:
        # Buscar la carpeta Caja_X en el path
        folder_name = None
        for part in p.parts:
            if isinstance(part, str) and part.lower().startswith("caja_"):
                folder_name = part
                break
        
        if folder_name:
            if folder_name not in files_by_folder:
                files_by_folder[folder_name] = []
            files_by_folder[folder_name].append(p)
        else:
            # Si no tiene carpeta Caja_X, ponerlo en "otros"
            if "otros" not in files_by_folder:
                files_by_folder["otros"] = []
            files_by_folder["otros"].append(p)
    
    # Ordenar carpetas y tomar solo las primeras 5
    sorted_folders = sorted([f for f in files_by_folder.keys() if f != "otros"])
    if "otros" in files_by_folder:
        sorted_folders.append("otros")
    
    selected_folders = sorted_folders[:10]
    files = []
    for folder in selected_folders:
        files.extend(files_by_folder[folder])
    
    files = sorted(files)  # Reordenar todos los archivos
    
    print(f"📁 Carpetas encontradas: {len(files_by_folder)}")
    print(f"📁 Carpetas seleccionadas (primeras 10): {', '.join(selected_folders)}")
    print(f"📦 Archivos OCR encontrados: {len(files)}")

    # ---- Pipeline: construir textos + embed + upsert
    chunk_size = args.chunk_size
    overlap = args.overlap
    batch_embed = args.batch_embed
    batch_upsert = args.batch_upsert
    skip_existing = not args.force

    to_embed: List[str] = []
    to_payloads: List[Dict[str, Any]] = []

    total_points = 0
    total_skipped = 0
    t0 = time.time()

    def flush_embed_and_upsert() -> int:
        nonlocal to_embed, to_payloads, total_points
        if not to_embed:
            return 0

        # Generar embeddings usando sentence-transformers
        vectors = embed_model.encode(to_embed, show_progress_bar=False, convert_to_numpy=True)
        # Convertir a lista de listas si es necesario
        if hasattr(vectors, 'tolist'):
            vectors = vectors.tolist()

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
        # real_path / doc_key: ruta relativa al directorio OCR (Caja_X/archivo.json)
        doc_key = str(json_path.relative_to(ocr_dir)).replace("\\", "/")
        source_path_str = str(json_path)
        _dbg(f"--- Archivo {idx}/{len(files)}: {doc_key} ---")

        doc = safe_json_load(json_path)
        if not doc:
            _dbg(f"   Saltando: JSON no cargó")
            continue

        pages = ocr_json_to_pages_text(doc)
        if not pages:
            _dbg(f"   Saltando: sin páginas extraíbles")
            continue

        original_num_pages = get_original_num_pages(doc, pages)
        _dbg(f"   original_num_pages={original_num_pages}")

        # Algoritmo: verificar si el documento ya está en Qdrant
        doc_exists = document_exists_in_qdrant(
            client_q, collection, doc_key, source_path=source_path_str
        )
        _dbg(f"   doc_exists={doc_exists} skip_existing={skip_existing}")

        max_page_in_qdrant = get_max_page_num_for_doc_key(
            client_q, collection, doc_key, source_path=source_path_str
        ) if doc_exists else None
        _dbg(f"   max_page_in_qdrant={max_page_in_qdrant}")

        # Si existe, páginas coinciden y skip_existing → omitir
        if doc_exists and skip_existing and max_page_in_qdrant is not None and max_page_in_qdrant == original_num_pages:
            total_skipped += 1
            print(f"⏭️  Saltando (ya existe, páginas OK): {doc_key}")
            _dbg(f"   DECISIÓN: SKIP (existe, páginas OK)")
            continue

        # Si existe pero páginas no coinciden, o force mode → eliminar y resubir
        if doc_exists:
            _dbg(f"   DECISIÓN: DELETE + RE-UPLOAD")
            delete_points_by_doc_key(client_q, collection, doc_key, source_path=source_path_str)
            if max_page_in_qdrant is not None and max_page_in_qdrant != original_num_pages:
                print(f"🔄 Re-subiendo (páginas cambiaron: Qdrant={max_page_in_qdrant} vs local={original_num_pages}): {doc_key}")
            else:
                print(f"🔄 Re-subiendo: {doc_key}")
        else:
            _dbg(f"   DECISIÓN: UPLOAD (nuevo documento)")

        meta = derive_meta_from_doc(doc, json_path)

        # Estrategia: chunk por página (mejor trazabilidad)
        # Si querés chunk global del documento, se puede cambiar.
        for page_num, page_text in pages:
            chunks = chunk_text(page_text, chunk_size=chunk_size, overlap=overlap)
            if not chunks:
                continue

            for ci, chunk in enumerate(chunks):
                payload = {
                    "doc_type": "ocr",
                    "doc_key": doc_key,
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
    print(f"🏁 Ingesta finalizada. Puntos totales: {total_points}. Documentos omitidos: {total_skipped}. Tiempo: {dt:.1f}s")


if __name__ == "__main__":
    main()

