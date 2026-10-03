"""
Maitri Krishi Assistant - AI Chat & RAG Endpoints
-------------------------------------------------
POST /api/chat         - Primary RAG chatbot endpoint
POST /api/chat/message - Alias endpoint
POST /api/chat/debug   - Developer RAG debug endpoint (inspect chunks & scores)
GET  /api/chat/status  - Status, vector store stats & model information
"""

import os
from typing import Optional, Dict, Any, List, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_current_user, is_elevated_user
from ..models import User, Farm, FarmPlan
from ..services.chat_service import process_chat_message, DEFAULT_OPENROUTER_MODEL
from ..services.rag_service import query_knowledge_base, get_chroma_collection
from ..services.iot_service import get_latest_telemetry

router = APIRouter()


class ChatContext(BaseModel):
    crop: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = Field(default=None, max_length=150)
    farm_id: Optional[int] = Field(default=None)
    soil_type: Optional[str] = Field(default=None, max_length=100)
    land_area: Optional[float] = Field(default=None, ge=0)
    crop_age_days: Optional[int] = Field(default=None, ge=0)
    soil_moisture: Optional[float] = Field(default=None, ge=0, le=100)
    temperature: Optional[float] = Field(default=None, ge=-50, le=70)
    previous_crop: Optional[str] = Field(default=None, max_length=100)
    sowing_date: Optional[str] = Field(default=None, max_length=50)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=2000)


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Farmer message/question")
    context: Optional[ChatContext] = Field(default=None, description="Optional crop/soil/farm context")
    history: Optional[List[ChatTurn]] = Field(default=None, max_length=10, description="Recent conversation turns (max 10)")
    model: Optional[str] = Field(default=None, description="Optional override for OpenRouter model")


class SourceItem(BaseModel):
    title: Optional[str] = None
    section: Optional[str] = None
    source: Optional[str] = None
    organization: Optional[str] = None
    category: Optional[str] = None
    crop: Optional[str] = None
    score: Optional[float] = None
    url: Optional[str] = None
    source_type: Optional[str] = None
    source_tier: Optional[str] = None
    published_date: Optional[str] = None


class ChatMessageResponse(BaseModel):
    reply: str
    sources: Optional[List[SourceItem]] = []
    retrieved_chunks: Optional[int] = 0
    confidence: Optional[float] = 0.0
    language: Optional[str] = "en"
    provider: Optional[str] = "openrouter"
    intent: Optional[str] = None
    route: Optional[str] = None
    requires_context: Optional[List[str]] = None
    live_lookup_attempted: Optional[bool] = None
    live_lookup_provider: Optional[str] = None
    live_lookup_result: Optional[str] = None
    rejection_reason: Optional[str] = None


class ChatDebugRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: Optional[int] = Field(default=4, ge=1, le=20, description="Top K knowledge chunks (1-20)")


def _enrich_user_farm_context(db: Session, user: Optional[User], client_context: Optional[Any]) -> Dict[str, Any]:
    """Combines client-provided context with authenticated farmer's real farm and IoT data."""
    if hasattr(client_context, "model_dump"):
        ctx = client_context.model_dump(exclude_unset=True)
    elif isinstance(client_context, dict):
        ctx = dict(client_context)
    else:
        ctx = {}

    # Anonymous requests must not supply an arbitrary farm_id
    if not user:
        ctx.pop("farm_id", None)
    else:
        req_farm_id = ctx.get("farm_id")
        if req_farm_id is not None:
            # Query exactly that farm belonging to the authenticated user
            farm = db.query(Farm).filter(Farm.id == req_farm_id, Farm.user_id == user.id).first()
            if not farm:
                # Disallow cross-user farm access and do not silently fallback
                ctx.pop("farm_id", None)
        else:
            # Preserve newest farm fallback behavior
            farm = db.query(Farm).filter(Farm.user_id == user.id).order_by(Farm.id.desc()).first()

        if farm:
            ctx["farm_id"] = farm.id
            if not ctx.get("farm_name") and farm.name:
                ctx["farm_name"] = farm.name
            if not ctx.get("crop") and farm.current_crop:
                ctx["crop"] = farm.current_crop
            if not ctx.get("soil_type") and farm.soil_type:
                ctx["soil_type"] = farm.soil_type
            if not ctx.get("land_area") and farm.area:
                ctx["land_area"] = farm.area
            if not ctx.get("location") and farm.location_name:
                ctx["location"] = farm.location_name
            if not ctx.get("previous_crop") and farm.previous_crop:
                ctx["previous_crop"] = farm.previous_crop
            if not ctx.get("sowing_date") and farm.sowing_date:
                ctx["sowing_date"] = farm.sowing_date

            plan = db.query(FarmPlan).filter(FarmPlan.farm_id == farm.id).order_by(FarmPlan.id.desc()).first()
            if plan and not ctx.get("crop") and plan.selected_crop:
                ctx["crop"] = plan.selected_crop

    # Inject latest IoT readings if moisture/temp are not explicitly passed
    if ctx.get("soil_moisture") is None or ctx.get("temperature") is None:
        try:
            latest_iot = get_latest_telemetry(db)
            if latest_iot and getattr(latest_iot, "is_online", False):
                if ctx.get("soil_moisture") is None and latest_iot.soil_moisture is not None:
                    ctx["soil_moisture"] = round(latest_iot.soil_moisture, 1)
                if ctx.get("temperature") is None and latest_iot.temperature is not None:
                    ctx["temperature"] = round(latest_iot.temperature, 1)
        except Exception:
            pass

    return ctx


@router.post("", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
@router.post("/", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
@router.post("/message", response_model=ChatMessageResponse, status_code=status.HTTP_200_OK)
def send_chat_message(
    payload: ChatMessageRequest,
    user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """
    Primary RAG endpoint for Maitri Krishi Assistant AI Chatbot.
    Ingests message, performs ChromaDB vector retrieval, enriches context, and queries OpenRouter.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter your farming question."
        )

    context_dict = payload.context.model_dump(exclude_unset=True) if payload.context else {}
    enriched_context = _enrich_user_farm_context(db, user, context_dict)

    # Server-side model allowlist applied to both authenticated and anonymous callers
    allowed_models = {
        DEFAULT_OPENROUTER_MODEL,
        os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    }
    chat_allowed = os.getenv("CHAT_ALLOWED_MODELS", "")
    if chat_allowed:
        for m in chat_allowed.split(","):
            if m.strip():
                allowed_models.add(m.strip())

    selected_model = None
    if payload.model:
        if payload.model in allowed_models:
            selected_model = payload.model
        else:
            selected_model = None  # Safely fallback to server default

    history_dicts = [t.model_dump() for t in payload.history] if payload.history else None

    response_data = process_chat_message(
        message=payload.message,
        context=enriched_context,
        history=history_dicts,
        model=selected_model
    )

    return response_data


@router.post("/debug", status_code=status.HTTP_200_OK)
def debug_rag_retrieval(
    payload: ChatDebugRequest,
    user: Optional[Any] = Depends(get_optional_current_user)
):
    """
    Development debug endpoint to inspect exact chunks, scores, and sources retrieved for a query.
    Requires authorized operator privileges and disabled in production.
    """
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RAG debug inspection endpoint disabled in production."
        )
    if not user or not is_elevated_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Authorized Agriculture / Seva Operators."
        )
    clamped_top_k = max(1, min(int(payload.top_k or 4), 20))
    return query_knowledge_base(payload.query, top_k=clamped_top_k)


@router.get("/status", status_code=status.HTTP_200_OK)
def get_chat_status(db: Session = Depends(get_db)):
    """Returns RAG vector database status and assistant configuration."""
    has_api_key = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    model = os.getenv("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    
    database_url = os.getenv("DATABASE_URL", "")
    is_postgres = database_url.startswith(("postgresql://", "postgres://"))
    
    if is_postgres:
        try:
            from sqlalchemy import text
            chunk_count = db.execute(text("SELECT COUNT(*) FROM public.knowledge_chunks")).scalar() or 0
            vector_store = "Supabase pgvector (384-d, HNSW)"
        except Exception:
            chunk_count = 0
            vector_store = "Supabase pgvector"
    else:
        collection = get_chroma_collection()
        chunk_count = collection.count() if collection else 0
        vector_store = "ChromaDB"

    return {
        "status": "online",
        "assistant_name": "Maitri Krishi Assistant",
        "architecture": "RAG (Retrieval-Augmented Generation)",
        "vector_store": vector_store,
        "vector_store_chunks_count": chunk_count,
        "openrouter_configured": has_api_key,
        "active_model": model,
        "supported_languages": ["English", "Hindi (हिन्दी)", "Hinglish"],
        "knowledge_base_categories": [
            "crops", "diseases", "pests", "fertilizers", "irrigation", "soil", "schemes", "crop_residue", "weather", "mountain_farming"
        ]
    }
