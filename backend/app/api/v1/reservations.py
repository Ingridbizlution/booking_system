"""預約 API：CRUD、衝突判定、審批、check-in。"""
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import (
    Reservation, ReservationAttendee, Resource, User, AuditLog,
    Location, Branch, UserGroup, UserGroupMember,
)
from ...schemas import (
    ReservationOut, ReservationCreate, ReservationUpdate, ReservationApproveIn,
)
from ..deps import get_current_user

router = APIRouter(prefix="/reservations", tags=["reservation"])


def _to_out(r: Reservation, db: Session) -> ReservationOut:
    organizer = db.get(User, r.organizer_id)
    resource = db.get(Resource, r.resource_id)
    return ReservationOut(
        id=r.id,
        organization_id=r.organization_id,
        resource_id=r.resource_id,
        organizer_id=r.organizer_id,
        title=r.title,
        start_at=r.start_at,
        end_at=r.end_at,
        type=r.type,
        status=r.status,
        approved_by=r.approved_by,
        check_in_at=r.check_in_at,
        notes=r.notes,
        created_at=r.created_at,
        access_code=r.access_code,
        organizer_name=organizer.display_name if organizer else None,
        resource_name=resource.name if resource else None,
        attendees=[
            {"id": a.id, "user_id": a.user_id, "external_email": a.external_email, "response": a.response}
            for a in r.attendees
        ],
    )


def _has_conflict(db: Session, resource_id: int, start_at, end_at, exclude_id: int | None = None) -> bool:
    """回傳是否與該資源既有已核准／已報到的預約重疊。"""
    stmt = select(Reservation).where(
        Reservation.resource_id == resource_id,
        Reservation.status.in_(["approved", "checked_in", "pending"]),
        # 時間重疊：new.start < existing.end AND new.end > existing.start
        and_(Reservation.start_at < end_at, Reservation.end_at > start_at),
    )
    if exclude_id:
        stmt = stmt.where(Reservation.id != exclude_id)
    return db.execute(stmt).first() is not None


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    resource_id: int | None = None,
    from_at: datetime | None = None,
    to_at: datetime | None = None,
    status_filter: str | None = None,
    approvable_by_me: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Reservation).where(Reservation.organization_id == user.organization_id)
    if resource_id:
        stmt = stmt.where(Reservation.resource_id == resource_id)
    if from_at:
        stmt = stmt.where(Reservation.end_at >= from_at)
    if to_at:
        stmt = stmt.where(Reservation.start_at <= to_at)
    if status_filter:
        stmt = stmt.where(Reservation.status == status_filter)
    rows = db.execute(stmt.order_by(Reservation.start_at.desc())).scalars().all()
    if approvable_by_me:
        rows = [r for r in rows if _can_approve_reservation(db, user, r)]
    return [_to_out(r, db) for r in rows]


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.end_at <= payload.start_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "結束時間必須晚於開始時間")

    resource = db.get(Resource, payload.resource_id)
    if not resource or resource.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "資源不存在")
    if resource.status != "available":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "資源目前不可預約")

    if _has_conflict(db, payload.resource_id, payload.start_at, payload.end_at):
        raise HTTPException(status.HTTP_409_CONFLICT, "此時段與現有預約衝突")

    # 生成 6 位存取代碼
    access_code = f"{secrets.randbelow(1000000):06d}"

    # 若資源設定「需要批准政策」，則預約進入待審批狀態；否則直接核准
    initial_status = "pending" if getattr(resource, "requires_approval", False) else "approved"

    r = Reservation(
        organization_id=user.organization_id,
        resource_id=payload.resource_id,
        organizer_id=user.id,
        title=payload.title,
        start_at=payload.start_at,
        end_at=payload.end_at,
        type=payload.type,
        status=initial_status,
        notes=payload.notes,
        access_code=access_code,
    )
    db.add(r)
    db.flush()

    for uid in payload.attendee_user_ids:
        db.add(ReservationAttendee(reservation_id=r.id, user_id=uid, response="pending"))
    for email in payload.attendee_external_emails:
        db.add(ReservationAttendee(reservation_id=r.id, external_email=email, response="pending"))

    db.add(AuditLog(
        organization_id=user.organization_id,
        actor_id=user.id,
        action="CREATE",
        target_type="reservation",
        target_id=r.id,
        context={"title": r.title, "resource_id": r.resource_id},
    ))
    db.commit()
    db.refresh(r)
    return _to_out(r, db)


@router.patch("/{rid}", response_model=ReservationOut)
def update_reservation(
    rid: int, payload: ReservationUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    r = db.get(Reservation, rid)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # 主辦人可修改；或有權核准此預約的管理員也可修改
    if r.organizer_id != user.id and not _can_approve_reservation(db, user, r):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "沒有權限修改此預約（僅主辦人或有權審批的管理員）")

    start_at = payload.start_at or r.start_at
    end_at = payload.end_at or r.end_at
    if end_at <= start_at:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "結束時間必須晚於開始時間")

    # 換會議室：重新驗證新資源、對新資源做衝突檢查
    new_resource_id = payload.resource_id if payload.resource_id is not None else r.resource_id
    if new_resource_id != r.resource_id:
        new_res = db.get(Resource, new_resource_id)
        if not new_res or new_res.organization_id != user.organization_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "新資源不存在")
        if new_res.status != "available":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "新資源目前不可預約")
    if _has_conflict(db, new_resource_id, start_at, end_at, exclude_id=r.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "此時段與現有預約衝突")

    data = payload.model_dump(exclude_unset=True)
    attendee_ids = data.pop("attendee_user_ids", None)
    for k, v in data.items():
        setattr(r, k, v)

    # 換與會者：整批取代
    if attendee_ids is not None:
        db.query(ReservationAttendee).filter(
            ReservationAttendee.reservation_id == r.id,
            ReservationAttendee.user_id.isnot(None),
        ).delete()
        for uid in attendee_ids:
            db.add(ReservationAttendee(reservation_id=r.id, user_id=uid, response="pending"))

    db.add(AuditLog(
        organization_id=user.organization_id, actor_id=user.id,
        action="UPDATE", target_type="reservation", target_id=r.id,
    ))
    db.commit()
    db.refresh(r)
    return _to_out(r, db)


def _room_branch_id(db: Session, room: Resource) -> int | None:
    """房間所屬的分支 id：優先看 resource.branch_id，否則由 location.branch_id 反推。"""
    if room.branch_id:
        return room.branch_id
    if room.location_id:
        loc = db.get(Location, room.location_id)
        if loc:
            return loc.branch_id
    return None


def _ancestor_branch_ids(db: Session, branch_id: int) -> list[int]:
    """回傳 [自己, parent, grandparent, ...] 直到根。"""
    chain: list[int] = []
    cur = branch_id
    guard = 0
    while cur and guard < 10:  # 防迴圈
        chain.append(cur)
        b = db.get(Branch, cur)
        if not b or not b.parent_branch_id:
            break
        cur = b.parent_branch_id
        guard += 1
    return chain


def _is_admin_user(db: Session, u: User) -> bool:
    """判斷是否為管理員：user.permissions.is_super_admin 或 屬於 category=admin 的群組。"""
    perms = u.permissions or {}
    if perms.get("is_super_admin"):
        return True
    rows = db.execute(
        select(UserGroup)
        .join(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
        .where(UserGroupMember.user_id == u.id, UserGroup.category == "admin")
    ).scalars().first()
    return rows is not None


def _can_approve_reservation(db: Session, approver: User, reservation: Reservation) -> bool:
    """
    核准權限：
      approver 必須為管理員（is_super_admin 或 admin 群組成員）
      且 approver.branch_id 必須在該房間分支的 ancestor chain 內
      （所屬分支或上層分支皆可）。
    """
    if not _is_admin_user(db, approver):
        return False
    room = db.get(Resource, reservation.resource_id)
    if not room:
        return False
    room_branch_id = _room_branch_id(db, room)
    if not room_branch_id:
        # 房間無分支 → 只有 super_admin 或組織任一 admin 可核准
        return True
    if not approver.branch_id:
        # 管理員未綁分支 → 視為總部級 → 可核准所有分支
        return True
    allowed = _ancestor_branch_ids(db, room_branch_id)
    return approver.branch_id in allowed


@router.post("/{rid}/approve", response_model=ReservationOut)
def approve_reservation(
    rid: int, payload: ReservationApproveIn,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    r = db.get(Reservation, rid)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not _can_approve_reservation(db, user, r):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "您沒有權限核准此預約（只有會議室所屬分支管理員或其上層分支管理員可核准）"
        )
    r.status = "approved" if payload.approve else "rejected"
    r.approved_by = user.id
    if payload.note:
        r.notes = (r.notes or "") + f"\n[approver] {payload.note}"
    db.add(AuditLog(
        organization_id=user.organization_id, actor_id=user.id,
        action="APPROVE" if payload.approve else "REJECT",
        target_type="reservation", target_id=r.id,
    ))
    db.commit()
    db.refresh(r)
    return _to_out(r, db)


@router.post("/{rid}/check-in", response_model=ReservationOut)
def check_in(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Reservation, rid)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    r.status = "checked_in"
    r.check_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(r)
    return _to_out(r, db)


@router.delete("/{rid}", status_code=204)
def cancel_reservation(rid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    r = db.get(Reservation, rid)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if r.organizer_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    r.status = "cancelled"
    db.add(AuditLog(
        organization_id=user.organization_id, actor_id=user.id,
        action="CANCEL", target_type="reservation", target_id=r.id,
    ))
    db.commit()
