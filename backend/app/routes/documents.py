"""
Secure Document Vault API Routes
---------------------------------
Enables farmers and authorized seva operators to archive and inspect:
- Land and Revenue Records
- Laboratory Soil Health Certificates
- PMFBY Insurance Receipts
- Welfare Scheme Application Acknowledgments

Integrated with Supabase Storage 'farmer-vault' private bucket
with per-user path isolation: {user_id}/{filename}
"""

import os
import re
import uuid
import logging
from pathlib import Path
from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db
from ..models import User, Farmer, Farm, FarmerDocument
from ..deps import (
    get_current_user,
    require_farmer_or_operator,
    is_same_user,
    is_elevated_user,
    get_authorized_farm,
    farm_belongs_to_farmer,
    get_farmer_for_user
)
from ..supabase_client import get_supabase_admin_client

logger = logging.getLogger("maitri.documents")
router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

# Server-side authoritative MIME mapping (Finding 7)
EXTENSION_TO_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def sanitize_filename(filename: str) -> str:
    clean = os.path.basename((filename or "doc").replace("\x00", ""))
    clean = re.sub(r"[^\w\.-]", "_", clean)
    return clean[:80]


def authorize_document_access(
    doc: FarmerDocument,
    current_user: Any,
    db: Session,
    action: str = "access"
) -> None:
    """
    Authorizes document operations based on current ownership of doc.farmer_id
    and elevated roles.
    A historical uploader does not retain access if they are no longer the owner
    of the farmer record associated with the document.
    """
    if is_elevated_user(current_user):
        return

    if not doc or not doc.farmer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: You cannot {action} this document."
        )

    farmer = db.query(Farmer).filter(Farmer.id == doc.farmer_id).first()
    if not farmer or not farmer.user_id or not is_same_user(farmer.user_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: You cannot {action} documents from another farmer's vault."
        )


@router.post("/upload")
async def upload_document(
    farmer_id: int = Form(...),
    document_name: str = Form(...),
    category: str = Form("Land Record"),
    farm_id: Optional[int] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(require_farmer_or_operator),
    db: Session = Depends(get_db)
):
    """
    Securely uploads and indexes a farmer document with category tagging.
    Authoritative storage is Supabase Storage 'farmer-vault' under {user_id}/{filename}.
    """
    farmer = db.query(Farmer).filter(Farmer.id == farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found")

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    is_elevated = is_elevated_user(current_user)

    # Tenant isolation: Farmers can only upload to their own vault
    if not is_elevated:
        if not farmer.user_id or not is_same_user(farmer.user_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You can only upload documents to your own vault."
            )

    real_farm_id = int(farm_id) if (isinstance(farm_id, int) or (isinstance(farm_id, str) and farm_id.isdigit())) else None
    if real_farm_id:
        farm = get_authorized_farm(db, real_farm_id, user=current_user, detail_forbidden="Farm does not belong to you")
        if not farm_belongs_to_farmer(farm, farmer):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Farm does not belong to the specified farmer."
            )

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Bounded read to prevent memory exhaustion (Finding 8)
    contents = await file.read(MAX_FILE_SIZE_BYTES + 1)
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    safe_name = sanitize_filename(Path(file.filename or "doc").stem)
    target_user_id = str(farmer.user_id) if farmer.user_id else f"farmer-{farmer.id}"
    stored_name = f"{farmer.maittri_farmer_id}_{uuid.uuid4().hex[:6]}_{safe_name}{ext}"
    storage_path = f"{target_user_id}/{stored_name}"

    # Server-derived MIME type ignoring untrusted client content_type (Finding 7)
    content_type = EXTENSION_TO_MIME.get(ext, "application/octet-stream")

    # Authoritative Upload: Direct to Supabase Storage 'farmer-vault'
    sb_client = get_supabase_admin_client()
    if not sb_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vault storage service unavailable: privileged storage client not configured."
        )

    try:
        sb_client.storage.from_("farmer-vault").upload(
            path=storage_path,
            file=contents,
            file_options={"content-type": content_type, "upsert": "false"}
        )
        logger.info(f"Directly uploaded {storage_path} to Supabase storage 'farmer-vault'")
    except Exception as e:
        logger.error(f"Failed to upload to Supabase storage: {e}")
        err_str = str(e).lower()
        if "already exists" in err_str or "duplicate" in err_str or "409" in err_str:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Document already exists in storage vault."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Storage vault upload failed. Please try again later."
        )

    dest_path = None

    doc = FarmerDocument(
        farmer_id=farmer.id,
        farm_id=real_farm_id,
        document_name=document_name.strip(),
        category=category,
        file_path="",
        storage_path=storage_path,
        file_type=ext.replace(".", "").upper(),
        file_size_bytes=len(contents),
        uploaded_by_user_id=current_user.id,
        uploader_role=user_role,
        status="VERIFIED"
    )
    db.add(doc)
    try:
        db.commit()
        db.refresh(doc)
    except Exception as db_exc:
        db.rollback()
        logger.error(f"Database commit failed after storage upload of {storage_path}: {db_exc}")
        try:
            sb_client.storage.from_("farmer-vault").remove([storage_path])
            logger.info(f"Cleaned up orphaned storage object {storage_path} after DB commit failure")
        except Exception as cleanup_exc:
            logger.error(f"Failed to clean up orphaned storage object {storage_path}: {cleanup_exc}")
        raise

    return {
        "id": doc.id,
        "farmer_id": doc.farmer_id,
        "farm_id": doc.farm_id,
        "document_name": doc.document_name,
        "category": doc.category,
        "file_type": doc.file_type,
        "file_size_kb": round(len(contents) / 1024, 1),
        "storage_path": doc.storage_path,
        "uploaded_at": doc.created_at.strftime("%Y-%m-%d %H:%M UTC") if doc.created_at else ""
    }


@router.get("")
def list_documents(
    farmer_id: Optional[int] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists verified documents with strict per-farmer isolation.
    """
    query = db.query(FarmerDocument)
    if not is_elevated_user(current_user):
        farmer = get_farmer_for_user(db, current_user.id)
        if farmer:
            query = query.filter(FarmerDocument.farmer_id == farmer.id)
        else:
            return []
    elif farmer_id is not None and isinstance(farmer_id, int):
        query = query.filter(FarmerDocument.farmer_id == farmer_id)

    if category is not None and isinstance(category, str) and category.strip():
        query = query.filter(FarmerDocument.category == category.strip())

    docs = query.order_by(FarmerDocument.id.desc()).all()
    return [
        {
            "id": d.id,
            "farmer_id": d.farmer_id,
            "farm_id": d.farm_id,
            "document_name": d.document_name,
            "category": d.category,
            "file_type": d.file_type,
            "file_size_kb": round((d.file_size_bytes or 0) / 1024, 1),
            "storage_path": d.storage_path,
            "status": d.status,
            "uploaded_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else ""
        }
        for d in docs
    ]


@router.get("/download/{doc_id}")
def download_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely streams document file for authorized user.
    Enforces that only the document owner or authorized operator/admin can download.
    """
    doc = db.query(FarmerDocument).filter(FarmerDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    authorize_document_access(doc, current_user, db, action="download")

    # Supabase storage download first (authoritative cloud vault)
    if doc.storage_path:
        sb = get_supabase_admin_client()
        if not sb:
            file_p = Path(doc.file_path) if doc.file_path else None
            if file_p and file_p.exists():
                safe_filename = f"{sanitize_filename(doc.document_name)}.{sanitize_filename(doc.file_type or 'bin').lower().strip('.')}"
                ext = f".{(doc.file_type or '').lower().strip('.')}"
                media_type = EXTENSION_TO_MIME.get(ext, "application/octet-stream")
                return FileResponse(path=str(file_p), filename=safe_filename, media_type=media_type)
            logger.error("Supabase privileged admin storage client is unavailable for document download")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vault storage service unavailable: privileged storage client not configured."
            )
        try:
            data = sb.storage.from_("farmer-vault").download(doc.storage_path)
            safe_filename = f"{sanitize_filename(doc.document_name)}.{sanitize_filename(doc.file_type or 'bin').lower().strip('.')}"
            ext = f".{(doc.file_type or '').lower().strip('.')}"
            media_type = EXTENSION_TO_MIME.get(ext, "application/octet-stream")
            return Response(
                content=data,
                media_type=media_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{safe_filename}"'
                }
            )
        except Exception as e:
            err_msg = str(e).lower()
            logger.error(f"Failed to download from Supabase storage for {doc.storage_path}: {e}", exc_info=True)
            # Check local storage fallback (for offline development/testing)
            file_p = Path(doc.file_path) if doc.file_path else None
            if file_p and file_p.exists():
                safe_filename = f"{sanitize_filename(doc.document_name)}.{sanitize_filename(doc.file_type or 'bin').lower().strip('.')}"
                ext = f".{(doc.file_type or '').lower().strip('.')}"
                media_type = EXTENSION_TO_MIME.get(ext, "application/octet-stream")
                return FileResponse(path=str(file_p), filename=safe_filename, media_type=media_type)

            if "not found" in err_msg or "404" in err_msg or "object not found" in err_msg:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found on storage vault.")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Storage vault service temporarily unavailable."
            )

    # Local storage fallback (for legacy/offline development files without storage_path)
    file_p = Path(doc.file_path) if doc.file_path else None
    if file_p and file_p.exists():
        safe_filename = f"{sanitize_filename(doc.document_name)}.{sanitize_filename(doc.file_type or 'bin').lower().strip('.')}"
        ext = f".{(doc.file_type or '').lower().strip('.')}"
        media_type = EXTENSION_TO_MIME.get(ext, "application/octet-stream")
        return FileResponse(
            path=str(file_p),
            filename=safe_filename,
            media_type=media_type
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found on storage vault or server.")


@router.get("/signed-url/{doc_id}")
def get_signed_url(
    doc_id: int,
    expires_in: int = Query(3600, ge=60, le=86400, description="Expiration time in seconds"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a secure, time-limited signed URL for viewing or downloading a vault document.
    Enforces that only the document owner or authorized operator/admin can generate a signed URL.
    """
    doc = db.query(FarmerDocument).filter(FarmerDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    authorize_document_access(doc, current_user, db, action="access")

    if not doc.storage_path:
        raise HTTPException(status_code=400, detail="Document has no remote storage path configured.")

    sb = get_supabase_admin_client()
    if not sb:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vault storage service unavailable: privileged storage client not configured."
        )

    try:
        signed_res = sb.storage.from_("farmer-vault").create_signed_url(doc.storage_path, expires_in)
        signed_url = None
        if isinstance(signed_res, dict):
            signed_url = signed_res.get("signedURL") or signed_res.get("signedUrl") or signed_res.get("url")
        elif hasattr(signed_res, "signed_url"):
            signed_url = getattr(signed_res, "signed_url")
        elif hasattr(signed_res, "signedURL"):
            signed_url = getattr(signed_res, "signedURL")
        elif hasattr(signed_res, "signedUrl"):
            signed_url = getattr(signed_res, "signedUrl")
        else:
            signed_url = str(signed_res)
        return {
            "status": "success",
            "doc_id": doc.id,
            "document_name": doc.document_name,
            "storage_path": doc.storage_path,
            "signed_url": signed_url,
            "expires_in_seconds": expires_in
        }
    except Exception as e:
        logger.error(f"Failed to generate signed URL for {doc.storage_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate secure document URL.")


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a document from the vault, ensuring ownership check.
    """
    doc = db.query(FarmerDocument).filter(FarmerDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    authorize_document_access(doc, current_user, db, action="delete")

    # Remove from Supabase Storage first
    if doc.storage_path:
        sb = get_supabase_admin_client()
        if not sb:
            logger.error(f"Cannot delete document {doc.id}: privileged storage client unavailable.")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vault storage service unavailable: privileged storage client not configured."
            )
        try:
            res = sb.storage.from_("farmer-vault").remove([doc.storage_path])
            if isinstance(res, dict) and res.get("error"):
                raise RuntimeError(str(res.get("error")))
        except Exception as e:
            logger.error(f"Failed to delete {doc.storage_path} from Supabase storage vault: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to delete document from storage vault. Database record preserved for retry."
            )

    # Remove local file if present
    if doc.file_path and Path(doc.file_path).exists():
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to remove local file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()

    return {"status": "success", "message": "Document deleted successfully", "id": doc_id}
