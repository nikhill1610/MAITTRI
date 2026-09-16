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
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db
from ..models import User, Farmer, Farm, FarmerDocument
from ..deps import get_current_user, require_farmer_or_operator, is_same_user
from ..supabase_client import get_supabase_admin_client, get_supabase_anon_client

logger = logging.getLogger("maitri.documents")
router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def sanitize_filename(filename: str) -> str:
    clean = os.path.basename((filename or "doc").replace("\x00", ""))
    clean = re.sub(r"[^\w\.-]", "_", clean)
    return clean[:80]


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
    is_elevated = user_role in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN")

    # Tenant isolation: Farmers can only upload to their own vault
    if not is_elevated:
        if farmer.user_id and not is_same_user(farmer.user_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You can only upload documents to your own vault."
            )

    if farm_id:
        farm = db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            raise HTTPException(status_code=404, detail="Farm not found")
        if not is_elevated and not is_same_user(farm.user_id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Farm does not belong to you")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Read and check size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    safe_name = sanitize_filename(Path(file.filename or "doc").stem)
    target_user_id = str(farmer.user_id or current_user.id)
    stored_name = f"{farmer.maittri_farmer_id}_{uuid.uuid4().hex[:6]}_{safe_name}{ext}"
    storage_path = f"{target_user_id}/{stored_name}"

    content_type = file.content_type or ("application/pdf" if ext == ".pdf" else f"image/{ext.replace('.', '')}")
    supabase_uploaded = False

    # Authoritative Upload: Direct to Supabase Storage 'farmer-vault'
    sb_client = get_supabase_admin_client() or get_supabase_anon_client()
    if sb_client:
        try:
            sb_client.storage.from_("farmer-vault").upload(
                path=storage_path,
                file=contents,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            supabase_uploaded = True
            logger.info(f"Directly uploaded {storage_path} to Supabase storage 'farmer-vault'")
        except Exception as e:
            logger.warning(f"Failed to upload to Supabase storage: {e}")

    # Fallback to local storage if Supabase is unavailable (e.g. offline dev/testing)
    dest_path = None
    if not supabase_uploaded:
        dest_path = UPLOAD_DIR / stored_name
        with open(dest_path, "wb") as f:
            f.write(contents)

    # Register in storage.objects table if PostgreSQL allows it directly
    try:
        db.execute(text("""
            INSERT INTO storage.objects (id, bucket_id, name, owner, created_at, updated_at)
            VALUES (gen_random_uuid(), 'farmer-vault', :name, :owner, now(), now())
            ON CONFLICT (bucket_id, name) DO NOTHING;
        """), {"name": storage_path, "owner": target_user_id})
    except Exception as e:
        logger.debug(f"Direct DB registration skipped: {e}")

    doc = FarmerDocument(
        farmer_id=farmer.id,
        farm_id=farm_id,
        document_name=document_name.strip(),
        category=category,
        file_path=str(dest_path) if dest_path else "",
        storage_path=storage_path,
        file_type=ext.replace(".", "").upper(),
        file_size_bytes=len(contents),
        uploaded_by_user_id=current_user.id,
        uploader_role=user_role,
        status="VERIFIED"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

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
    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()

    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
        farmer = db.query(Farmer).filter(Farmer.user_id == current_user.id).first()
        if farmer:
            query = query.filter(
                (FarmerDocument.farmer_id == farmer.id) | 
                (FarmerDocument.uploaded_by_user_id == current_user.id)
            )
        else:
            query = query.filter(FarmerDocument.uploaded_by_user_id == current_user.id)
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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
        farmer = db.query(Farmer).filter(Farmer.id == doc.farmer_id).first()
        owns_doc = (
            (farmer and str(farmer.user_id) == str(current_user.id)) or
            (doc.uploaded_by_user_id and str(doc.uploaded_by_user_id) == str(current_user.id))
        )
        if not owns_doc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot download documents from another farmer's vault."
            )

    # Supabase storage download first (authoritative cloud vault)
    if doc.storage_path:
        sb = get_supabase_admin_client() or get_supabase_anon_client()
        if sb:
            try:
                data = sb.storage.from_("farmer-vault").download(doc.storage_path)
                return Response(
                    content=data,
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f'attachment; filename="{doc.document_name}.{doc.file_type.lower()}"'
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to download from Supabase storage, falling back to local if available: {e}")

    # Local storage fallback (for offline development/testing)
    file_p = Path(doc.file_path) if doc.file_path else None
    if file_p and file_p.exists():
        return FileResponse(
            path=str(file_p),
            filename=f"{doc.document_name}.{doc.file_type.lower()}",
            media_type="application/octet-stream"
        )

    raise HTTPException(status_code=404, detail="File content not found on storage vault or server.")


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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
        farmer = db.query(Farmer).filter(Farmer.id == doc.farmer_id).first()
        owns_doc = (
            (farmer and str(farmer.user_id) == str(current_user.id)) or
            (doc.uploaded_by_user_id and str(doc.uploaded_by_user_id) == str(current_user.id))
        )
        if not owns_doc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot access documents from another farmer's vault."
            )

    if not doc.storage_path:
        raise HTTPException(status_code=400, detail="Document has no remote storage path configured.")

    sb = get_supabase_admin_client() or get_supabase_anon_client()
    if not sb:
        raise HTTPException(status_code=503, detail="Supabase storage client is unavailable.")

    try:
        signed_res = sb.storage.from_("farmer-vault").create_signed_url(doc.storage_path, expires_in)
        signed_url = (
            signed_res.get("signedURL")
            if isinstance(signed_res, dict)
            else (signed_res.get("signedUrl") if isinstance(signed_res, dict) else str(signed_res))
        )
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
        raise HTTPException(status_code=500, detail=f"Failed to create signed URL: {str(e)}")


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

    user_role = (getattr(current_user, "role", "FARMER") or "FARMER").upper()
    if user_role not in ("AUTHORIZED_OPERATOR", "OPERATOR", "ADMIN"):
        farmer = db.query(Farmer).filter(Farmer.id == doc.farmer_id).first()
        owns_doc = (
            (farmer and str(farmer.user_id) == str(current_user.id)) or
            (doc.uploaded_by_user_id and str(doc.uploaded_by_user_id) == str(current_user.id))
        )
        if not owns_doc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You cannot delete another farmer's document."
            )

    # Remove from Supabase Storage
    if doc.storage_path:
        sb = get_supabase_admin_client()
        if sb:
            try:
                sb.storage.from_("farmer-vault").remove([doc.storage_path])
            except Exception as e:
                logger.warning(f"Failed to remove {doc.storage_path} from Supabase storage: {e}")

    # Remove local file if present
    if doc.file_path and Path(doc.file_path).exists():
        try:
            os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"Failed to remove local file {doc.file_path}: {e}")

    db.delete(doc)
    db.commit()

    return {"status": "success", "message": "Document deleted successfully", "id": doc_id}
