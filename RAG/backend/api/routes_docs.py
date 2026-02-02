"""
Document routes for managing documents.
"""
import os
import tempfile
import logging
from pathlib import Path

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List, Optional

from backend.security.deps import get_current_user
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docs", tags=["docs"])


class PdfProxyRequest(BaseModel):
    """Request body for PDF proxy: backend downloads from signed URL and returns bytes."""
    signed_url: str

# Hetzner S3 Configuration
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")


def _remove_temp_file(path: str) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Could not remove temp PDF file %s: %s", path, e)


@router.post("/pdf-proxy")
async def pdf_proxy(
    body: PdfProxyRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Download PDF from the given signed URL to a temp file, stream it for in-browser
    display, then delete the temp file. Avoids triggering download when opening the viewer.
    """
    signed_url = (body.signed_url or "").strip()
    if not signed_url:
        raise HTTPException(status_code=400, detail="signed_url is required")

    tmp_path: Optional[Path] = None
    try:
        resp = requests.get(signed_url, timeout=60, stream=True)
        resp.raise_for_status()
        suffix = Path(signed_url.split("?")[0]).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            tmp_path = Path(f.name)
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        background_tasks.add_task(_remove_temp_file, str(tmp_path))
        return FileResponse(str(tmp_path), media_type="application/pdf")
    except requests.exceptions.Timeout:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        logger.warning("Timeout downloading PDF from signed URL")
        raise HTTPException(status_code=504, detail="Timeout downloading PDF")
    except requests.exceptions.RequestException as e:
        if tmp_path and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        logger.warning("Error downloading PDF from signed URL: %s", e)
        raise HTTPException(status_code=502, detail="Error downloading PDF from storage")


@router.get("/list")
async def list_documents(
    current_user: dict = Depends(get_current_user)
):
    """
    List available documents.
    
    Note: This will be implemented when we integrate with Hetzner Object Storage.
    """
    return {
        "documents": [],
        "total": 0
    }


@router.get("/signed-url")
async def get_signed_url(
    s3_key: str,
    expiration: int = 3600,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate a signed URL for accessing a document in Hetzner Object Storage.
    
    Args:
        s3_key: S3 key/path of the document (e.g., pdf/Caja_1/documento.pdf)
        expiration: URL expiration time in seconds (default: 3600 = 1 hour)
        
    Returns:
        Dictionary with signed_url
    """
    if not all([S3_ENDPOINT, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY]):
        raise HTTPException(
            status_code=500,
            detail="Hetzner S3 not configured. Missing S3 credentials in environment."
        )
    
    try:
        # Configure endpoint
        endpoint = S3_ENDPOINT
        if not endpoint.startswith(("http://", "https://")):
            endpoint = "https://" + endpoint
        
        # Create S3 client
        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
        )
        
        # Generate signed URL
        signed_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiration
        )
        
        logger.info(f"✅ Signed URL generated for: {s3_key}")
        return {
            "signed_url": signed_url,
            "s3_key": s3_key,
            "expiration_seconds": expiration
        }
        
    except ClientError as e:
        logger.error(f"❌ Error generating signed URL for {s3_key}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating signed URL: {str(e)}"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error generating signed URL: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@router.get("/{document_id}")
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get document metadata and signed URL.
    
    Note: This will be implemented when we integrate with Hetzner Object Storage.
    """
    return {
        "document_id": document_id,
        "signed_url": None,
        "metadata": {}
    }
