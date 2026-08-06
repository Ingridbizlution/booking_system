"""設備（Resource where type='equipment'）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import Resource, Location, Branch, User
from ...schemas import RoomOut, RoomCreate, RoomUpdate
from ..deps import get_current_user
# 沿用 rooms._to_out 產生 RoomOut（含 branch_name / location_name 反查）
from . import rooms as rooms_mod

router = APIRouter(prefix="/equipment", tags=["reservation"])


@router.get("", response_model=list[RoomOut])
def list_equipment(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Resource).where(
        Resource.organization_id == user.organization_id,
        Resource.type == "equipment",
    )
    equipment = db.execute(q.order_by(Resource.id)).scalars().all()
    return [rooms_mod._to_out(r, db) for r in equipment]


@router.post("", response_model=RoomOut, status_code=201)
def create_equipment(
    payload: RoomCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = Resource(
        organization_id=user.organization_id,
        type="equipment",
        subtype=payload.subtype or None,
        name=payload.name,
        capacity=payload.capacity or 0,
        category=payload.category,
        location_id=payload.location_id,
        image_url=payload.image_url,
        status=payload.status or "available",
        description=payload.description,
        branch_id=payload.branch_id,
        team_space=payload.team_space,
        requires_approval=payload.requires_approval,
        priority=payload.priority,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return rooms_mod._to_out(r, db)


@router.get("/{eq_id}", response_model=RoomOut)
def get_equipment(eq_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Resource, eq_id)
    if not r or r.organization_id != user.organization_id or r.type != "equipment":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return rooms_mod._to_out(r, db)


@router.patch("/{eq_id}", response_model=RoomOut)
def update_equipment(
    eq_id: int, payload: RoomUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    r = db.get(Resource, eq_id)
    if not r or r.organization_id != user.organization_id or r.type != "equipment":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return rooms_mod._to_out(r, db)


@router.delete("/{eq_id}", status_code=204)
def delete_equipment(eq_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Resource, eq_id)
    if not r or r.organization_id != user.organization_id or r.type != "equipment":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(r)
    db.commit()
