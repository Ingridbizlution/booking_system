"""可指派角色（Assignable Roles）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import User, UserGroup, AssignableRole
from ...schemas import AssignableRoleOut, AssignableRoleCreate, AssignableRoleUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/roles", tags=["organization"])


def _to_out(r: AssignableRole, bound_group_name: str | None) -> AssignableRoleOut:
    return AssignableRoleOut(
        id=r.id,
        organization_id=r.organization_id,
        name=r.name,
        description=r.description,
        icon=r.icon,
        bound_group_id=r.bound_group_id,
        bound_group_name=bound_group_name,
        is_enabled=r.is_enabled,
        created_at=r.created_at,
    )


def _bound_name(db: Session, gid: int | None) -> str | None:
    if not gid:
        return None
    g = db.get(UserGroup, gid)
    return g.name if g else None


@router.get("", response_model=list[AssignableRoleOut])
def list_roles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    roles = db.execute(
        select(AssignableRole)
        .where(AssignableRole.organization_id == user.organization_id)
        .order_by(AssignableRole.id)
    ).scalars().all()
    return [_to_out(r, _bound_name(db, r.bound_group_id)) for r in roles]


@router.post("", response_model=AssignableRoleOut, status_code=201)
def create_role(
    payload: AssignableRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    exists = db.execute(
        select(AssignableRole).where(
            AssignableRole.organization_id == user.organization_id,
            AssignableRole.name == payload.name,
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "此角色名稱已存在")

    if payload.bound_group_id:
        g = db.get(UserGroup, payload.bound_group_id)
        if not g or g.organization_id != user.organization_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "綁定的群組不存在")

    r = AssignableRole(organization_id=user.organization_id, **payload.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _to_out(r, _bound_name(db, r.bound_group_id))


@router.patch("/{role_id}", response_model=AssignableRoleOut)
def update_role(
    role_id: int,
    payload: AssignableRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.get(AssignableRole, role_id)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    data = payload.model_dump(exclude_unset=True)
    if "bound_group_id" in data and data["bound_group_id"]:
        g = db.get(UserGroup, data["bound_group_id"])
        if not g or g.organization_id != user.organization_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "綁定的群組不存在")

    for k, v in data.items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return _to_out(r, _bound_name(db, r.bound_group_id))


@router.delete("/{role_id}", status_code=204)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = db.get(AssignableRole, role_id)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(r)
    db.commit()
