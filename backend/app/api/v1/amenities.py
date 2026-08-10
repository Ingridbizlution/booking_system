"""附屬設備 CRUD + 資源關聯管理。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import Resource, Branch
from ...models.amenity import Amenity, ResourceAmenity
from ...schemas.amenity import AmenityOut, AmenityCreate, AmenityUpdate, ResourceAmenityIn
from ..deps import get_current_user, require_permission
from ...models import User

router = APIRouter(prefix="/amenities", tags=["reservation"])


def _to_out(a: Amenity, db: Session) -> AmenityOut:
    branch_name = None
    if a.branch_id:
        b = db.get(Branch, a.branch_id)
        if b:
            branch_name = b.name

    links = db.execute(
        select(ResourceAmenity.resource_id).where(ResourceAmenity.amenity_id == a.id)
    ).scalars().all()

    room_ids, desk_ids, equipment_ids, parking_ids, other_ids = [], [], [], [], []
    if links:
        resources = db.execute(
            select(Resource.id, Resource.type).where(Resource.id.in_(links))
        ).all()
        for rid, rtype in resources:
            if rtype == "room":
                room_ids.append(rid)
            elif rtype == "desk":
                desk_ids.append(rid)
            elif rtype == "equipment":
                equipment_ids.append(rid)
            elif rtype == "parking":
                parking_ids.append(rid)
            else:
                other_ids.append(rid)

    return AmenityOut(
        id=a.id,
        organization_id=a.organization_id,
        name=a.name,
        icon=a.icon,
        branch_id=a.branch_id,
        branch_name=branch_name,
        created_at=a.created_at,
        updated_at=a.updated_at,
        room_ids=room_ids,
        desk_ids=desk_ids,
        equipment_ids=equipment_ids,
        parking_ids=parking_ids,
        other_ids=other_ids,
    )


@router.get("", response_model=list[AmenityOut])
def list_amenities(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Amenity)
        .where(Amenity.organization_id == user.organization_id)
        .order_by(Amenity.id)
    ).scalars().all()
    return [_to_out(a, db) for a in rows]


@router.post("", response_model=AmenityOut, status_code=201)
def create_amenity(
    payload: AmenityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    a = Amenity(
        organization_id=user.organization_id,
        name=payload.name,
        icon=payload.icon,
        branch_id=payload.branch_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return _to_out(a, db)


@router.get("/{amenity_id}", response_model=AmenityOut)
def get_amenity(
    amenity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.get(Amenity, amenity_id)
    if not a or a.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return _to_out(a, db)


@router.patch("/{amenity_id}", response_model=AmenityOut)
def update_amenity(
    amenity_id: int,
    payload: AmenityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    a = db.get(Amenity, amenity_id)
    if not a or a.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    db.refresh(a)
    return _to_out(a, db)


@router.delete("/{amenity_id}", status_code=204)
def delete_amenity(
    amenity_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    a = db.get(Amenity, amenity_id)
    if not a or a.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.execute(delete(ResourceAmenity).where(ResourceAmenity.amenity_id == a.id))
    db.delete(a)
    db.commit()


@router.put("/{amenity_id}/rooms", response_model=AmenityOut)
def set_amenity_rooms(
    amenity_id: int,
    payload: ResourceAmenityIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    return _set_resources(amenity_id, "room", payload.resource_ids, db, user)


@router.put("/{amenity_id}/equipment", response_model=AmenityOut)
def set_amenity_equipment(
    amenity_id: int,
    payload: ResourceAmenityIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    return _set_resources(amenity_id, "equipment", payload.resource_ids, db, user)


def _set_resources(amenity_id, rtype, resource_ids, db, user):
    a = db.get(Amenity, amenity_id)
    if not a or a.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    existing = db.execute(
        select(ResourceAmenity.resource_id)
        .join(Resource, Resource.id == ResourceAmenity.resource_id)
        .where(ResourceAmenity.amenity_id == a.id, Resource.type == rtype)
    ).scalars().all()

    to_remove = set(existing) - set(resource_ids)
    to_add = set(resource_ids) - set(existing)

    if to_remove:
        db.execute(
            delete(ResourceAmenity).where(
                ResourceAmenity.amenity_id == a.id,
                ResourceAmenity.resource_id.in_(to_remove),
            )
        )
    for rid in to_add:
        r = db.get(Resource, rid)
        if r and r.organization_id == user.organization_id and r.type == rtype:
            db.add(ResourceAmenity(amenity_id=a.id, resource_id=rid))

    db.commit()
    db.refresh(a)
    return _to_out(a, db)
