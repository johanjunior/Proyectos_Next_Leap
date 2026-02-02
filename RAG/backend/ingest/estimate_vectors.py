import json
import math
import re
from pathlib import Path
from collections import defaultdict

OCR_ROOT = Path("data/OCR")   # ajusta si tu ruta es distinta
CHUNK_SIZE = 1200            # debe coincidir con tu ingest real

PAGE_RE = re.compile(r"^pag_(\d+)$")

def page_sort_key(k: str) -> int:
    m = PAGE_RE.match(k)
    return int(m.group(1)) if m else 10**12  # al final si no matchea

def safe_read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="latin-1"))
        except Exception:
            return None

def count_chunks_for_text(text: str, chunk_size: int) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    return math.ceil(len(text) / chunk_size)

def main():
    # Busca archivos JSON dentro de Caja_*/
    files = sorted([p for p in OCR_ROOT.rglob("*.json") if p.is_file() and p.name != "entrega_ocr_20260126.json"])
    print(f"📦 Archivos OCR encontrados: {len(files)}")

    totals = {
        "files_ok": 0,
        "files_bad": 0,
        "pages": 0,
        "chars": 0,
        "chunks": 0,
    }

    # Para ver distribución por caja
    by_box = defaultdict(lambda: {"files": 0, "pages": 0, "chunks": 0})

    for fp in files:
        data = safe_read_json(fp)
        if not data:
            totals["files_bad"] += 1
            continue

        paginas = data.get("paginas", {})
        if not isinstance(paginas, dict) or not paginas:
            totals["files_ok"] += 1
            # archivo válido pero sin páginas
            box = fp.parent.name  # Caja_123
            by_box[box]["files"] += 1
            continue

        # Ordenar páginas pag_1, pag_2, ... pag_10 ...
        page_keys = sorted(paginas.keys(), key=page_sort_key)

        # Concatenar texto de todas las páginas
        texts = []
        page_count = 0
        char_count = 0

        for pk in page_keys:
            page_obj = paginas.get(pk, {})
            if isinstance(page_obj, dict):
                t = (page_obj.get("texto") or "").strip()
            else:
                t = ""
            if t:
                texts.append(t)
                char_count += len(t)
            page_count += 1

        full_text = "\n\n".join(texts)
        chunks = count_chunks_for_text(full_text, CHUNK_SIZE)

        totals["files_ok"] += 1
        totals["pages"] += page_count
        totals["chars"] += char_count
        totals["chunks"] += chunks

        box = fp.parent.name  # Caja_1
        by_box[box]["files"] += 1
        by_box[box]["pages"] += page_count
        by_box[box]["chunks"] += chunks

    print("\n✅ RESULTADOS")
    print(f"  Archivos OK: {totals['files_ok']}")
    print(f"  Archivos con error: {totals['files_bad']}")
    print(f"  Total páginas: {totals['pages']}")
    print(f"  Total caracteres OCR: {totals['chars']:,}")
    print(f"  Total chunks (≈ vectores): {totals['chunks']:,}")
    if totals["files_ok"] > 0:
        print(f"  Promedio páginas/archivo: {totals['pages'] / totals['files_ok']:.2f}")
        print(f"  Promedio chunks/archivo: {totals['chunks'] / totals['files_ok']:.2f}")

    # Top 10 cajas por chunks
    top = sorted(by_box.items(), key=lambda kv: kv[1]["chunks"], reverse=True)[:10]
    print("\n📦 Top 10 cajas por chunks:")
    for box, s in top:
        print(f"  {box}: files={s['files']}, pages={s['pages']}, chunks={s['chunks']}")

if __name__ == "__main__":
    main()

