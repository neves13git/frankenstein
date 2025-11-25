
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from models.system1 import System1
from schemas.system1 import System1Read, System1Update

router = APIRouter()

# Endpoint para buscar um sistema por id
@router.get("/system1/id/{system_id}", response_model=System1Read)
def get_system_by_id(system_id: int, db: Session = Depends(get_db)):
    system = db.query(System1).filter(System1.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    return system

# Endpoint para atualizar um sistema por id
@router.put("/system1/id/{system_id}", response_model=System1Read)
def update_system_by_id(system_id: int, system_update: System1Update = Body(...), db: Session = Depends(get_db)):
    system = db.query(System1).filter(System1.id == system_id).first()
    if not system:
        raise HTTPException(status_code=404, detail="System not found")
    for field, value in system_update.dict(exclude_unset=True).items():
        setattr(system, field, value)
    db.commit()
    db.refresh(system)
    return system


# Retorna todos os sistemas
@router.get("/system1", response_model=List[System1Read])
def read_systems(db: Session = Depends(get_db)):
    systems = db.query(System1).all()
    return systems

# Retorna sistemas filtrados por client_id
@router.get("/system1/{client_id}", response_model=List[System1Read])
def read_systems_by_client(client_id: int, db: Session = Depends(get_db)):
    systems = db.query(System1).filter(System1.client_id == client_id).all()
    return systems