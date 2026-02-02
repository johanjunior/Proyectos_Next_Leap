"""
Subida de archivos a Hetzner Object Storage (S3-compatible).
Unifica la lógica de subida de PDF y OCR en un solo módulo.
"""
import argparse
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

# ================= CONFIG =================

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")

if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY]):
    raise RuntimeError("Faltan variables S3 en el .env (S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY)")

# ================= S3 CLIENT =================


def get_s3_client():
    """Cliente boto3 configurado para Hetzner Object Storage."""
    endpoint = S3_ENDPOINT
    if not endpoint.startswith(("http://", "https://")):
        endpoint = "https://" + endpoint

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
    )


# ================= UPLOAD LOGIC =================


def _upload_to_s3(source_subdir: str, s3_prefix: str, extension: str, type_name: str) -> tuple[int, int]:
    """
    Sube archivos desde data/{source_subdir}/ a S3 bajo el prefijo {s3_prefix}/.
    extension: ej. ".pdf" o ".json"
    type_name: nombre para los mensajes (ej. "PDF", "JSON")
    Returns:
        (uploaded_count, skipped_count)
    """
    source_dir = os.path.join(DATA_DIR, source_subdir)

    if not os.path.isdir(source_dir):
        raise RuntimeError(f"No existe el directorio fuente: {source_dir}")

    s3 = get_s3_client()

    print(f"\n📂 Escaneando: {source_dir}\n")

    uploaded = 0
    skipped = 0

    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            if not filename.lower().endswith(extension):
                skipped += 1
                continue

            local_path = os.path.join(root, filename)
            rel_path = os.path.relpath(local_path, source_dir)
            rel_path_normalized = rel_path.replace("\\", "/")
            s3_key = f"{s3_prefix}/{rel_path_normalized}"

            print(f"⬆️  Subiendo: {rel_path_normalized}")
            print(f"    → s3://{S3_BUCKET}/{s3_key}")

            try:
                with open(local_path, "rb") as f:
                    s3.upload_fileobj(f, S3_BUCKET, s3_key)
                uploaded += 1
            except Exception as e:
                print(f"    ❌ Error al subir: {e}")
                skipped += 1

    print(f"\n✅ Subida finalizada ({type_name}).")
    print(f"   📄 Archivos subidos: {uploaded}")
    if skipped > 0:
        print(f"   ⏭️  Archivos omitidos: {skipped}\n")

    return uploaded, skipped


def upload_pdfs() -> tuple[int, int]:
    """Sube todos los PDF desde data/PDF/ a S3 bajo el prefijo 'pdf/'."""
    return _upload_to_s3("PDF", "pdf", ".pdf", "PDF")


def upload_ocr_files() -> tuple[int, int]:
    """Sube todos los JSON desde data/OCR/ a S3 bajo el prefijo 'ocr/'."""
    return _upload_to_s3("OCR", "ocr", ".json", "OCR")


# ================= CLI =================


def main():
    parser = argparse.ArgumentParser(
        description="Subir archivos a Hetzner Object Storage (S3-compatible)."
    )
    parser.add_argument(
        "tipo",
        nargs="?",
        choices=["pdf", "ocr", "all"],
        default="all",
        help="Tipo de archivos a subir: pdf, ocr, o all (por defecto)",
    )
    args = parser.parse_args()

    if args.tipo == "pdf":
        upload_pdfs()
    elif args.tipo == "ocr":
        upload_ocr_files()
    else:
        upload_pdfs()
        print()
        upload_ocr_files()


if __name__ == "__main__":
    main()
