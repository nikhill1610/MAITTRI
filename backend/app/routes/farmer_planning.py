"""
farmer_planning.py
FastAPI route endpoints for MAITTRI Personal Farm Planner & Crop Calendar.
Tagline: "किसान का साथी, समृद्धि की शुरुआत"

Provides endpoints for personalized, date-based farming plans,
today's goals, 7-day weekly plans, complete crop lifecycle timeline,
task completions, and digital farm diary.
"""

import json
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models import Farm, FarmPlan, FarmPlanTask, FarmPlanCompletion
from ..deps import get_current_user
from ..schemas import (
    FarmerPlanCreateRequest,
    FarmerPlanUpdateRequest,
    TaskStatusUpdateRequest,
    FarmerNoteRequest
)
from ..services.farmer_planning_service import (
    parse_date_safely,
    calculate_sowing_date_from_age,
    calculate_sowing_date_from_stage,
    generate_full_farm_plan_data,
    create_or_update_persisted_plan,
    mark_farm_task_complete,
    add_task_farmer_note,
    get_farm_diary_history
)
from ..services.crop_calendar_service import (
    get_crop_calendar,
    list_crop_calendars
)

router = APIRouter()
calendar_router = APIRouter()


# =====================================================================
# 1. CROP CALENDAR INDEPENDENT ENDPOINTS
# =====================================================================

@calendar_router.get("", response_model=List[Dict[str, Any]])
def get_all_crop_calendars():
    """Returns authoritative ICAR/SAU crop calendars for all supported crops."""
    return list_crop_calendars()


@calendar_router.get("/{crop_name}")
def get_single_crop_calendar(crop_name: str):
    """Returns authoritative ICAR/SAU crop calendar for a single crop."""
    cal = get_crop_calendar(crop_name)
    if not cal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop calendar for '{crop_name}' is currently unavailable."
        )
    return cal


# =====================================================================
# 2. FARMER PLANNING CORE ENDPOINTS
# =====================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
def create_farmer_plan(
    payload: FarmerPlanCreateRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Creates or recalculates a personalized farm plan based on sowing date,
    crop age, or current crop stage. Enforces farm ownership.
    """
    farm = db.query(Farm).filter(Farm.id == payload.farm_id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")

    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN") and str(farm.user_id) != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Cannot create plan for another farmer's farm."
            )

    # Resolve sowing date
    resolved_sowing_date: Optional[date] = None
    if payload.sowing_date:
        resolved_sowing_date = parse_date_safely(payload.sowing_date)

    if not resolved_sowing_date and payload.crop_age_days is not None:
        resolved_sowing_date = calculate_sowing_date_from_age(payload.crop_age_days)
    elif not resolved_sowing_date and payload.current_stage:
        resolved_sowing_date = calculate_sowing_date_from_stage(payload.crop, payload.current_stage)

    # Fallback to existing farm.sowing_date if present
    if not resolved_sowing_date and getattr(farm, "sowing_date", None):
        resolved_sowing_date = parse_date_safely(farm.sowing_date)

    if not resolved_sowing_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid sowing date, crop age in days, or current crop stage."
        )

    user_id = user.id if user else farm.user_id
    plan_record, plan_data = create_or_update_persisted_plan(
        db=db,
        user_id=user_id,
        farm_id=farm.id,
        crop_name=payload.crop,
        sowing_date=resolved_sowing_date,
        variety=payload.variety
    )

    return {
        "success": True,
        "message": "Personalized farm plan generated successfully.",
        "plan": plan_data
    }


@router.get("")
def list_farmer_plans(
    farm_id: Optional[int] = Query(None, description="Optional farm ID filter"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Lists saved personalized farm plans with tenant isolation."""
    query = db.query(FarmPlan)
    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            user_farm_ids = [f.id for f in db.query(Farm).filter(Farm.user_id == user.id).all()]
            query = query.filter(
                (FarmPlan.user_id == user.id) |
                (FarmPlan.farm_id.in_(user_farm_ids))
            )
    if farm_id is not None:
        query = query.filter(FarmPlan.farm_id == farm_id)

    plans = query.order_by(desc(FarmPlan.updated_at)).all()
    results = []
    for p in plans:
        results.append({
            "id": p.id,
            "farm_id": p.farm_id,
            "crop": p.selected_crop,
            "sowing_date": p.sowing_date,
            "variety": p.variety,
            "current_stage": p.current_stage,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        })
    return {"plans": results}


@router.get("/{plan_id}")
def get_farmer_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """
    Retrieves full details of a personalized farm plan.
    Enforces ownership isolation.
    """
    plan = db.query(FarmPlan).filter(FarmPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm plan not found")

    farm = db.query(Farm).filter(Farm.id == plan.farm_id).first()
    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            if str(plan.user_id) != str(user.id) and (not farm or str(farm.user_id) != str(user.id)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Farm plan belongs to another farmer."
                )

    sowing_date = parse_date_safely(plan.sowing_date)
    if not sowing_date:
        sowing_date = plan.created_at.date() if plan.created_at else date.today()

    plan_data = generate_full_farm_plan_data(
        crop_name=plan.selected_crop,
        sowing_date=sowing_date,
        farm=farm,
        db=db,
        variety=plan.variety
    )
    plan_data["plan_id"] = plan.id

    # Retrieve synced database task status
    today_str = plan_data["reference_date"]
    db_tasks = db.query(FarmPlanTask).filter(
        FarmPlanTask.farm_plan_id == plan.id,
        FarmPlanTask.task_date == today_str
    ).all()
    task_map = {t.title: t for t in db_tasks}

    for t in plan_data["today_goals"]["top_3_priorities"]:
        if t["title"] in task_map:
            t["id"] = task_map[t["title"]].id
            t["status"] = task_map[t["title"]].status

    for t in plan_data["today_goals"]["other_tasks"]:
        if t["title"] in task_map:
            t["id"] = task_map[t["title"]].id
            t["status"] = task_map[t["title"]].status

    return plan_data


@router.get("/{plan_id}/today")
def get_today_farm_goals(
    plan_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Returns today's farm goals, top 3 priorities, and 'Why MAITTRI recommends this'."""
    full_plan = get_farmer_plan(plan_id, db, user=user)
    return {
        "crop": full_plan["crop"],
        "crop_age_days": full_plan["crop_age_days"],
        "current_stage": full_plan["current_stage"],
        "today_goals": full_plan["today_goals"],
        "weather_context": full_plan["weather_context"],
        "iot_context": full_plan["iot_context"]
    }


@router.get("/{plan_id}/week")
def get_weekly_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Returns the dynamic 7-day plan (This Week's Plan)."""
    full_plan = get_farmer_plan(plan_id, db, user=user)
    return {
        "crop": full_plan["crop"],
        "week_plan": full_plan["week_plan"]
    }


@router.get("/{plan_id}/timeline")
def get_lifecycle_timeline(
    plan_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Returns the complete crop lifecycle timeline with real dates."""
    full_plan = get_farmer_plan(plan_id, db, user=user)
    return {
        "crop": full_plan["crop"],
        "sowing_date": full_plan["sowing_date"],
        "timeline": full_plan["timeline"],
        "weekly_milestones": full_plan["weekly_milestones"]
    }


@router.patch("/tasks/{task_id}")
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdateRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Updates task status (pending/completed/skipped) with ownership verification."""
    task = db.query(FarmPlanTask).filter(FarmPlanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task #{task_id} not found")

    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            plan = db.query(FarmPlan).filter(FarmPlan.id == task.farm_plan_id).first()
            if plan and str(plan.user_id) != str(user.id):
                farm = db.query(Farm).filter(Farm.id == plan.farm_id).first()
                if not farm or str(farm.user_id) != str(user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Task belongs to another farmer's plan."
                    )

    try:
        res = mark_farm_task_complete(db, task_id=task_id, status=payload.status, notes=payload.notes)
        return {"success": True, "task": res}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/tasks/{task_id}/complete")
def complete_task(
    task_id: int,
    payload: Optional[TaskStatusUpdateRequest] = None,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Marks task completed with optional farmer note and logs to farm diary."""
    task = db.query(FarmPlanTask).filter(FarmPlanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task #{task_id} not found")

    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            plan = db.query(FarmPlan).filter(FarmPlan.id == task.farm_plan_id).first()
            if plan and str(plan.user_id) != str(user.id):
                farm = db.query(Farm).filter(Farm.id == plan.farm_id).first()
                if not farm or str(farm.user_id) != str(user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Task belongs to another farmer's plan."
                    )

    notes = payload.notes if payload else None
    try:
        res = mark_farm_task_complete(db, task_id=task_id, status="completed", notes=notes)
        return {"success": True, "task": res, "message": "Task marked as completed and saved to Farm Diary."}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/tasks/{task_id}/note")
def add_note_to_task(
    task_id: int,
    payload: FarmerNoteRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Adds or updates a farmer observation note for a task."""
    task = db.query(FarmPlanTask).filter(FarmPlanTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task #{task_id} not found")

    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            plan = db.query(FarmPlan).filter(FarmPlan.id == task.farm_plan_id).first()
            if plan and str(plan.user_id) != str(user.id):
                farm = db.query(Farm).filter(Farm.id == plan.farm_id).first()
                if not farm or str(farm.user_id) != str(user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Task belongs to another farmer's plan."
                    )

    try:
        res = add_task_farmer_note(db, task_id=task_id, notes=payload.notes)
        return {"success": True, "message": "Farmer note saved to Farm Diary.", "data": res}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{plan_id}/history")
def get_farm_diary(
    plan_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """Returns all completed tasks and historical observations in the Digital Farm Diary."""
    plan = db.query(FarmPlan).filter(FarmPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm plan not found")

    if user:
        role = (getattr(user, "role", None) or "FARMER").upper()
        if role not in ("AUTHORIZED_OPERATOR", "ADMIN"):
            if str(plan.user_id) != str(user.id):
                farm = db.query(Farm).filter(Farm.id == plan.farm_id).first()
                if not farm or str(farm.user_id) != str(user.id):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied: Farm diary belongs to another farmer."
                    )

    diary_records = get_farm_diary_history(db, farm_plan_id=plan.id)
    return {
        "plan_id": plan.id,
        "crop": plan.selected_crop,
        "diary_entries": diary_records,
        "total_completed": len(diary_records)
    }
