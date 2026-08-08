"""審核規則 API：CRUD。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import User, AuditLog
from ...models.booking_policy import BookingPolicy, BookingPolicyApprover
from ...schemas.booking_policy import (
    BookingPolicyOut, BookingPolicyCreate, BookingPolicyUpdate, ApproverOut,
)
from ..deps import get_current_user

router = APIRouter(prefix="/booking-policies", tags=["booking-policy"])


def _to_out(bp: BookingPolicy) -> BookingPolicyOut:
    return BookingPolicyOut(
        id=bp.id,
        organization_id=bp.organization_id,
        name=bp.name,
        lock_slot=bp.lock_slot,
        conditional_mode=bp.conditional_mode,
        conditions=bp.conditions or [],
        re_approve_mode=bp.re_approve_mode,
        show_approver=bp.show_approver,
        auto_reject_days=bp.auto_reject_days,
        approvers=[
            ApproverOut(id=a.id, approver_type=a.approver_type, approver_id=a.approver_id)
            for a in bp.approvers
        ],
        created_at=bp.created_at.isoformat() if bp.created_at else None,
        updated_at=bp.updated_at.isoformat() if bp.updated_at else None,
    )


def _sync_approvers(db: Session, bp: BookingPolicy, approvers_in: list):
    db.query(BookingPolicyApprover).filter(
        BookingPolicyApprover.booking_policy_id == bp.id
    ).delete()
    for a in approvers_in:
        db.add(BookingPolicyApprover(
            booking_policy_id=bp.id,
            approver_type=a.type,
            approver_id=a.id,
        ))


@router.get("", response_model=list[BookingPolicyOut])
def list_booking_policies(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(BookingPolicy)
        .where(BookingPolicy.organization_id == user.organization_id)
        .order_by(BookingPolicy.id)
    ).scalars().all()
    return [_to_out(bp) for bp in rows]


@router.get("/{bp_id}", response_model=BookingPolicyOut)
def get_booking_policy(
    bp_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bp = db.get(BookingPolicy, bp_id)
    if not bp or bp.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "審核規則不存在")
    return _to_out(bp)


@router.post("", response_model=BookingPolicyOut, status_code=201)
def create_booking_policy(
    payload: BookingPolicyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bp = BookingPolicy(
        organization_id=user.organization_id,
        name=payload.name,
        lock_slot=payload.lock_slot,
        conditional_mode=payload.conditional_mode,
        conditions=payload.conditions,
        re_approve_mode=payload.re_approve_mode,
        show_approver=payload.show_approver,
        auto_reject_days=payload.auto_reject_days,
    )
    db.add(bp)
    db.flush()

    _sync_approvers(db, bp, payload.approvers)

    db.add(AuditLog(
        organization_id=user.organization_id,
        actor_id=user.id,
        action="CREATE",
        target_type="booking_policy",
        target_id=bp.id,
        context={"name": bp.name},
    ))
    db.commit()
    db.refresh(bp)
    return _to_out(bp)


@router.patch("/{bp_id}", response_model=BookingPolicyOut)
def update_booking_policy(
    bp_id: int,
    payload: BookingPolicyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bp = db.get(BookingPolicy, bp_id)
    if not bp or bp.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "審核規則不存在")

    data = payload.model_dump(exclude_unset=True)
    approvers_in = data.pop("approvers", None)

    for k, v in data.items():
        setattr(bp, k, v)

    if approvers_in is not None:
        _sync_approvers(db, bp, payload.approvers)

    db.add(AuditLog(
        organization_id=user.organization_id,
        actor_id=user.id,
        action="UPDATE",
        target_type="booking_policy",
        target_id=bp.id,
    ))
    db.commit()
    db.refresh(bp)
    return _to_out(bp)


@router.delete("/{bp_id}", status_code=204)
def delete_booking_policy(
    bp_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    bp = db.get(BookingPolicy, bp_id)
    if not bp or bp.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "審核規則不存在")

    db.add(AuditLog(
        organization_id=user.organization_id,
        actor_id=user.id,
        action="DELETE",
        target_type="booking_policy",
        target_id=bp.id,
        context={"name": bp.name},
    ))
    db.delete(bp)
    db.commit()
