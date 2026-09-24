"""
Maitri Krishi Assistant - AI Chat & RAG Endpoints
-------------------------------------------------
POST /api/chat         - Primary RAG chatbot endpoint
POST /api/chat/message - Alias endpoint
POST /api/chat/debug   - Developer RAG debug endpoint (inspect chunks & scores)
GET  /api/chat/status  - Status, vector store stats & model information
"""

import os
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_optional_current_user
from ..models import User, Farm, FarmPlan
from ..services.chat_service import process_chat_message, DEFAULT_OPENROUTER_MODEL
from ..services.rag_service import query_knowledge_base, get_chroma_collection
from ..services.iot_service import get_latest_telemetry

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Farmer message/question")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Optional crop/soil/farm context")
    history: Optional[List[Dict[str, str]]] = Field(default=None, description="Recent conversation turns")
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
    top_k: Optional[int] = 4


def _enrich_user_farm_context(db: Session, user: Optional[User], client_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Combines client-provided context with authenticated farmer's real farm and IoT data."""
    ctx = dict(client_context) if client_context else {}

    # If user is logged in, load farm profile
    if user:
        farm = db.query(Farm).filter(Farm.user_id == user.id).order_by(Farm.id.desc()).first()
        if farm:
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

    enriched_context = _enrich_user_farm_context(db, user, payload.context)

    response_data = process_chat_message(
        message=payload.message,
        context=enriched_context,
        history=payload.history,
        model=payload.model
    )

    return response_data


@router.post("/debug", status_code=status.HTTP_200_OK)
def debug_rag_retrieval(payload: ChatDebugRequest):
    """
    Development debug endpoint to inspect exact chunks, scores, and sources retrieved for a query.
    Disabled in production.
    """
    if os.getenv("ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RAG debug inspection endpoint disabled in production."
        )
    return query_knowledge_base(payload.query, top_k=payload.top_k or 4)


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
