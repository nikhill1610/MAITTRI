from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Farm, FarmPlan
from ..schemas import FarmCreate, FarmResponse, FarmUpdate
from ..deps import get_current_user

router = APIRouter()

@router.post("", response_model=FarmResponse)
def create_farm(payload: FarmCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = Farm(user_id=user.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm

@router.get("", response_model=list[FarmResponse])
def list_farms(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Farm).filter(Farm.user_id == user.id).order_by(Farm.id.desc()).all()

@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(farm_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    return farm

@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(farm_id: int, payload: FarmUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(farm, key, value)
        
    db.commit()
    db.refresh(farm)
    return farm

@router.delete("/{farm_id}")
def delete_farm(farm_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    farm = db.query(Farm).filter(Farm.id == farm_id, Farm.user_id == user.id).first()
    if not farm:
        raise HTTPException(404, "Farm not found")
    
    db.query(FarmPlan).filter(FarmPlan.farm_id == farm_id).delete()
    db.delete(farm)
    db.commit()
    return {"message": "Farm deleted successfully", "id": farm_id}

