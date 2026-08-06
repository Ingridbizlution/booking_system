"""分支機構與地點。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import Branch, Location, User
from ...schemas import BranchOut, BranchCreate, LocationOut, LocationCreate
from ..deps import get_current_user

router = APIRouter(prefix="/branches", tags=["organization"])


@router.get("", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(Branch).where(Branch.organization_id == user.organization_id).order_by(Branch.id)
    ).scalars().all()
    return rows


@router.post("", response_model=BranchOut, status_code=201)
def create_branch(payload: BranchCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    br = Branch(organization_id=user.organization_id, **payload.model_dump())
    db.add(br)
    db.commit()
    db.refresh(br)
    return br


loc_router = APIRouter(prefix="/locations", tags=["organization"])


@loc_router.get("", response_model=list[LocationOut])
def list_locations(
    branch_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Location).join(Branch).where(Branch.organization_id == user.organization_id)
    if branch_id:
        q = q.where(Location.branch_id == branch_id)
    return db.execute(q.order_by(Location.id)).scalars().all()


@loc_router.post("", response_model=LocationOut, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    br = db.get(Branch, payload.branch_id)
    if not br or br.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "分支不存在")
    loc = Location(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _owns_location(loc: Location, db: Session, org_id: int) -> bool:
    br = db.get(Branch, loc.branch_id)
    return bool(br and br.organization_id == org_id)


@loc_router.patch("/{loc_id}", response_model=LocationOut)
def update_location(
    loc_id: int, payload: LocationCreate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    loc = db.get(Location, loc_id)
    if not loc or not _owns_location(loc, db, user.organization_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # 若改分支，確認新分支也屬於同一組織
    new_br = db.get(Branch, payload.branch_id)
    if not new_br or new_br.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "分支不存在或不屬於您的組織")
    for k, v in payload.model_dump().items():
        setattr(loc, k, v)
    db.commit()
    db.refresh(loc)
    return loc


@loc_router.delete("/{loc_id}", status_code=204)
def delete_location(
    loc_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    loc = db.get(Location, loc_id)
    if not loc or not _owns_location(loc, db, user.organization_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(loc)
    db.commit()
