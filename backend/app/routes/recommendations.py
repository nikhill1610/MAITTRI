from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Farm, FarmPlan
from ..schemas import RecommendationRequest, PlanRequest
from ..deps import get_current_user
from ..services import recommend, make_plan, analyze_nutrients
import json

router = APIRouter()

@router.post("")
def get_recommendations(payload: RecommendationRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = db.query(Farm).filter(Farm.id == payload.farm_id, Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return {
        "farm_id": farm.id,
        "nutrient_analysis": analyze_nutrients(farm),
        "recommendations": recommend(farm, payload.season, payload.budget)
    }

@router.post("/plan")
def create_plan(payload: PlanRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = db.query(Farm).filter(Farm.id == payload.farm_id, Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    try:
        plan = make_plan(farm, payload.crop)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        
    row = FarmPlan(farm_id=farm.id, selected_crop=payload.crop, plan_json=json.dumps(plan))
    db.add(row)
    db.commit()
    return plan
