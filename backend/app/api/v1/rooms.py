"""房間（Resource where type='room'）+ 暫停服務時間 (Blackouts)。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import Resource, ResourceBlackout, Location, Branch, User
from ...schemas import RoomOut, RoomCreate, RoomUpdate, BlackoutOut, BlackoutCreate
from ..deps import get_current_user

router = APIRouter(prefix="/rooms", tags=["reservation"])
blackout_router = APIRouter(prefix="/blackouts", tags=["reservation"])


def _to_out(room: Resource, db: Session) -> RoomOut:
    branch_name = None
    location_name = None
    if room.location_id:
        loc = db.get(Location, room.location_id)
        if loc:
            location_name = loc.name
            br = db.get(Branch, loc.branch_id)
            if br:
                branch_name = br.name
    # 若手動設定了 branch_id，優先用它
    if not branch_name and room.branch_id:
        br = db.get(Branch, room.branch_id)
        if br:
            branch_name = br.name

    combined_names: list[str] = []
    for rid in (room.combined_room_ids or []):
        src = db.get(Resource, rid)
        if src:
            combined_names.append(src.name)

    return RoomOut(
        id=room.id,
        organization_id=room.organization_id,
        type=room.type,
        subtype=room.subtype or "standard",
        name=room.name,
        capacity=room.capacity,
        category=room.category,
        location_id=room.location_id,
        image_url=room.image_url,
        status=room.status,
        qr_code=room.qr_code,
        location_name=location_name,
        branch_name=branch_name,
        description=room.description,
        branch_id=room.branch_id,
        combined_room_ids=room.combined_room_ids or [],
        combined_room_names=combined_names,
        team_space=bool(room.team_space),
        requires_approval=bool(room.requires_approval),
        priority=room.priority or 0,
    )


@router.get("", response_model=list[RoomOut])
def list_rooms(
    subtype: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(Resource).where(
        Resource.organization_id == user.organization_id,
        Resource.type == "room",
    )
    if subtype:
        q = q.where(Resource.subtype == subtype)
    rooms = db.execute(q.order_by(Resource.id)).scalars().all()
    return [_to_out(r, db) for r in rooms]


@router.post("", response_model=RoomOut, status_code=201)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    room = Resource(
        organization_id=user.organization_id,
        type="room",
        subtype=payload.subtype,
        name=payload.name,
        capacity=payload.capacity,
        category=payload.category,
        location_id=payload.location_id,
        image_url=payload.image_url,
        status=payload.status,
        description=payload.description,
        branch_id=payload.branch_id,
        combined_room_ids=payload.combined_room_ids or [],
        team_space=payload.team_space,
        requires_approval=payload.requires_approval,
    )
    db.add(room)
    db.commit()
    db.refresh(room)
    return _to_out(room, db)


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Resource, room_id)
    if not r or r.organization_id != user.organization_id or r.type != "room":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return _to_out(r, db)


@router.patch("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int, payload: RoomUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    r = db.get(Resource, room_id)
    if not r or r.organization_id != user.organization_id or r.type != "room":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _to_out(r, db)


@router.delete("/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Resource, room_id)
    if not r or r.organization_id != user.organization_id or r.type != "room":
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(r)
    db.commit()


# ---------- 暫停服務時間 (Blackout) ----------

def _owns_room(db: Session, room_id: int, org_id: int) -> Resource | None:
    r = db.get(Resource, room_id)
    if not r or r.organization_id != org_id or r.type != "room":
        return None
    return r


@router.get("/{room_id}/blackouts", response_model=list[BlackoutOut])
def list_blackouts(
    room_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _owns_room(db, room_id, user.organization_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    rows = db.execute(
        select(ResourceBlackout)
        .where(ResourceBlackout.resource_id == room_id)
        .order_by(ResourceBlackout.start_at.desc())
    ).scalars().all()
    return rows


@router.post("/{room_id}/blackouts", response_model=BlackoutOut, status_code=201)
def create_blackout(
    room_id: int,
    payload: BlackoutCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not _owns_room(db, room_id, user.organization_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if payload.end_at <= payload.start_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "結束時間必須晚於開始時間")
    bo = ResourceBlackout(
        resource_id=room_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        block_reservations=payload.block_reservations,
        public_note=payload.public_note,
        internal_note=payload.internal_note,
    )
    db.add(bo)
    db.commit()
    db.refresh(bo)
    return bo


@blackout_router.delete("/{blackout_id}", status_code=204)
def delete_blackout(
    blackout_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bo = db.get(ResourceBlackout, blackout_id)
    if not bo:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    room = db.get(Resource, bo.resource_id)
    if not room or room.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(bo)
    db.commit()
