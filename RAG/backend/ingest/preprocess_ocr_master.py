import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple


# =============================
# CONFIG (ajusta si necesitas)
# =============================

# Calcular rutas relativas al proyecto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
OCR_DIR = os.path.join(DATA_DIR, "OCR")

# Rutas de entrada y salida
INPUT_JSON = Path(OCR_DIR) / "entrega_ocr_20260126.json"
OUTPUT_ROOT = Path(OCR_DIR)  # aquí quedarán Caja_1/, Caja_10/, etc.

TOP_KEY = "conde_abogados"      # llave principal del maestro


# =============================
# Helpers
# =============================
def safe_filename(name: str, max_len: int = 180) -> str:
    """
    Convierte un nombre libre a nombre de archivo seguro:
    - elimina caracteres problemáticos
    - colapsa espacios
    - recorta longitud
    """
    name = name.strip()

    # Reemplaza separadores/riesgos por guion
    name = re.sub(r"[\/\\\:\*\?\"\<\>\|\n\r\t]+", " - ", name)

    # Colapsa espacios
    name = re.sub(r"\s+", " ", name).strip()

    # Quita puntos finales (evita rarezas)
    name = name.rstrip(" .")

    if len(name) > max_len:
        name = name[:max_len].rstrip(" -")

    # Si queda vacío, fallback
    return name or "documento_sin_nombre"


def ensure_unique_path(base_path: Path) -> Path:
    """
    Si el archivo ya existe, agrega sufijo _v2, _v3, etc.
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent

    i = 2
    while True:
        candidate = parent / f"{stem}_v{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def parse_caja_key(caja_key: str) -> str:
    """
    caja_key viene como 'caja_1' -> devuelve 'Caja_1'
    """
    m = re.match(r"caja_(\d+)", caja_key.strip().lower())
    if m:
        return f"Caja_{m.group(1)}"
    # fallback: capitaliza
    return caja_key.replace("caja_", "Caja_")


def build_output_dir(caja_key: str) -> Path:
    return OUTPUT_ROOT / parse_caja_key(caja_key)


def minimal_record_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Guarda un JSON por expediente manteniendo todo lo útil:
    - metadata
    - paginas (texto por página)
    - status, updated_at, link
    """
    # Puedes recortar si quieres que pese menos.
    # Por ahora lo guardo completo a partir del record del expediente.
    return record


# =============================
# Main
# =============================
def main() -> None:
    print("=" * 70)
    print("🚀 INICIANDO PREPROCESADO DE OCR MASTER")
    print("=" * 70)
    print(f"📂 Input JSON: {INPUT_JSON}")
    print(f"📁 Output root: {OUTPUT_ROOT}")
    print(f"🔑 Top key: {TOP_KEY}")
    print()

    # Verificar archivo de entrada
    print("🔍 [1/6] Verificando archivo de entrada...")
    if not INPUT_JSON.exists():
        raise FileNotFoundError(f"❌ No existe el input: {INPUT_JSON}")
    file_size = INPUT_JSON.stat().st_size / (1024 * 1024)  # MB
    print(f"   ✅ Archivo encontrado ({file_size:.2f} MB)")
    print()

    # Crear directorio de salida
    print("📁 [2/6] Preparando directorio de salida...")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ Directorio listo: {OUTPUT_ROOT}")
    print()

    # Cargar JSON
    print("📖 [3/6] Cargando JSON maestro...")
    try:
        data = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
        print(f"   ✅ JSON cargado exitosamente")
    except json.JSONDecodeError as e:
        raise ValueError(f"❌ Error al parsear JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"❌ Error al leer archivo: {e}")
    print()

    # Verificar estructura
    print("🔎 [4/6] Verificando estructura del JSON...")
    if TOP_KEY not in data:
        raise KeyError(f"❌ No se encontró la llave '{TOP_KEY}' en el JSON maestro")
    root = data[TOP_KEY]
    if not isinstance(root, dict):
        raise ValueError(f"❌ La llave '{TOP_KEY}' no contiene un diccionario")
    
    # Contar estructura antes de procesar
    total_sedes = len(root)
    total_cajas = sum(
        len([k for k, v in sede_obj.items() if isinstance(v, dict)])
        for sede_obj in root.values()
        if isinstance(sede_obj, dict)
    )
    print(f"   ✅ Estructura válida: {total_sedes} sede(s), {total_cajas} caja(s) encontrada(s)")
    print()

    # Procesar datos
    print("⚙️  [5/6] Procesando expedientes...")
    print("-" * 70)
    
    total_docs = 0
    total_written = 0
    skipped = 0
    current_sede = None
    current_caja = None
    sede_count = 0
    caja_count = 0

    # Estructura: conde_abogados -> Florencia -> caja_1 -> "001" -> record
    for sede, sede_obj in root.items():
        if not isinstance(sede_obj, dict):
            print(f"   ⚠️  Sede '{sede}' ignorada (no es diccionario)")
            continue

        sede_count += 1
        current_sede = sede
        print(f"\n📍 Procesando SEDE [{sede_count}/{total_sedes}]: {sede}")

        for caja_key, caja_obj in sede_obj.items():
            if not isinstance(caja_obj, dict):
                print(f"   ⚠️  Caja '{caja_key}' ignorada (no es diccionario)")
                continue

            caja_count += 1
            current_caja = parse_caja_key(caja_key)
            out_dir = build_output_dir(caja_key)
            out_dir.mkdir(parents=True, exist_ok=True)
            
            expedientes_en_caja = len([k for k, v in caja_obj.items() if isinstance(v, dict)])
            print(f"   📦 Caja [{caja_count}/{total_cajas}]: {current_caja} ({expedientes_en_caja} expedientes)")

            expediente_count = 0
            for exp_id, record in caja_obj.items():
                total_docs += 1
                expediente_count += 1

                if not isinstance(record, dict):
                    skipped += 1
                    if expediente_count <= 3:  # Solo mostrar primeros errores
                        print(f"      ⚠️  Expediente '{exp_id}' ignorado (no es diccionario)")
                    continue

                md = record.get("metadata") or {}
                nombre = md.get("nombre")

                # fallback si no existe nombre
                if not nombre or not isinstance(nombre, str):
                    nombre = f"{sede}_{current_caja}_{exp_id}"

                fname = safe_filename(nombre) + ".json"
                out_path = ensure_unique_path(out_dir / fname)

                # Mostrar progreso cada 10 expedientes o en los primeros 3
                if expediente_count <= 3 or expediente_count % 10 == 0:
                    print(f"      📄 [{expediente_count}/{expedientes_en_caja}] {fname}")

                payload = minimal_record_payload(record)

                # útil: agregar sede y caja normalizada aunque ya venga en metadata
                payload.setdefault("metadata", {})
                if isinstance(payload["metadata"], dict):
                    payload["metadata"].setdefault("sede", sede)
                    # si metadata.caja viene como "1", conservamos
                    payload["metadata"].setdefault("caja_key", current_caja)
                    payload["metadata"].setdefault("exp_id", exp_id)

                try:
                    out_path.write_text(
                        json.dumps(payload, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    total_written += 1
                except Exception as e:
                    print(f"      ❌ Error al escribir {fname}: {e}")
                    skipped += 1

            print(f"      ✅ Caja {current_caja} completada: {expedientes_en_caja} expedientes procesados")

    print()
    print("-" * 70)
    print("✅ [6/6] Preprocesado finalizado")
    print("=" * 70)
    print(f"📊 RESUMEN:")
    print(f"   📄 Documentos encontrados: {total_docs}")
    print(f"   ✅ Archivos escritos: {total_written}")
    print(f"   ⏭️  Omitidos: {skipped}")
    print(f"   📁 Sede(s) procesada(s): {sede_count}")
    print(f"   📦 Caja(s) procesada(s): {caja_count}")
    print(f"   📂 Output root: {OUTPUT_ROOT}")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

