import os
import sys
import boto3
from botocore.exceptions import ClientError

try:
    from dotenv import load_dotenv
    load_dotenv()  # carga .env si existe
except Exception:
    # Si no tienes python-dotenv, no pasa nada: seguirá leyendo variables del sistema
    pass


def must_getenv(key: str) -> str:
    v = os.getenv(key)
    if not v:
        raise RuntimeError(f"Falta variable de entorno: {key}")
    return v


def main():
    endpoint = must_getenv("S3_ENDPOINT")
    bucket = must_getenv("S3_BUCKET")
    access_key = must_getenv("S3_ACCESS_KEY")
    secret_key = must_getenv("S3_SECRET_KEY")

    # Cliente S3 apuntando a Hetzner
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    print("\n[1/4] Listando buckets visibles con estas credenciales...")
    try:
        resp = s3.list_buckets()
        buckets = [b["Name"] for b in resp.get("Buckets", [])]
        print("Buckets:", buckets)
    except ClientError as e:
        print("ERROR list_buckets:", e)
        sys.exit(1)

    if bucket not in buckets:
        print(f"\n⚠️  El bucket '{bucket}' no aparece en list_buckets().")
        print("   - Revisa que el nombre sea exacto")
        print("   - Revisa que el Access Key sea del Object Storage correcto")
        # Aun así intentamos operar sobre el bucket por si el proveedor limita el listado:
        # (algunos setups restringen list_buckets)
    else:
        print(f"✅ Bucket objetivo encontrado: {bucket}")

    print("\n[2/4] Subiendo marcadores de carpetas (pdf/.keep y ocr/.keep)...")
    for key in ["pdf/.keep", "ocr/.keep"]:
        try:
            s3.put_object(Bucket=bucket, Key=key, Body=b"")
            print(f"✅ Subido: s3://{bucket}/{key}")
        except ClientError as e:
            print(f"ERROR put_object {key}:", e)
            sys.exit(1)

    print("\n[3/4] Verificando que existan los objetos subidos (list_objects_v2)...")
    try:
        resp = s3.list_objects_v2(Bucket=bucket, Prefix="")
        keys = [obj["Key"] for obj in resp.get("Contents", [])]
        print("Objetos (primeros 50):", keys[:50])
        if "pdf/.keep" in keys and "ocr/.keep" in keys:
            print("✅ Verificación OK: ambos .keep están presentes.")
        else:
            print("⚠️  No veo uno o ambos .keep en el listado. Revisa permisos o prefix.")
    except ClientError as e:
        print("ERROR list_objects_v2:", e)
        sys.exit(1)

    print("\n[4/4] OK — Conexión estable y permisos correctos.\n")


if __name__ == "__main__":
    main()

