"""可指派角色（Assignable Roles）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy import func
from ...db.session import get_db
from ...models import User, UserGroup, AssignableRole, UserRoleAssignment, Branch
from ...schemas import (
    AssignableRoleOut, AssignableRoleCreate, AssignableRoleUpdate,
    RoleAssignmentIn, RoleAssignmentOut,
)
from ...core.rbac import in_branch_scope
from ..deps import get_current_user, require_permission

router = APIRouter(prefix="/roles", tags=["organization"])


def _to_out(r: AssignableRole, bound_group_name: str | None, assignee_count: int = 0) -> AssignableRoleOut:
    return AssignableRoleOut(
        id=r.id,
        organization_id=r.organization_id,
        name=r.name,
        description=r.description,
        icon=r.icon,
        bound_group_id=r.bound_group_id,
        bound_group_name=bound_group_name,
        key=r.key,
        assignee_count=assignee_count,
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
    rows = db.execute(
        select(AssignableRole, func.count(UserRoleAssignment.id))
        .outerjoin(UserRoleAssignment, UserRoleAssignment.role_id == AssignableRole.id)
        .where(AssignableRole.organization_id == user.organization_id)
        .group_by(AssignableRole.id)
        .order_by(AssignableRole.id)
    ).all()
    return [_to_out(r, _bound_name(db, r.bound_group_id), cnt or 0) for r, cnt in rows]


@router.post("", response_model=AssignableRoleOut, status_code=201)
def create_role(
    payload: AssignableRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
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
    user: User = Depends(require_permission("user")),
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
    user: User = Depends(require_permission("user")),
):
    r = db.get(AssignableRole, role_id)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(r)
    db.commit()


# ---------------- 角色指派 ----------------

def _owned_role(db: Session, role_id: int, user: User) -> AssignableRole:
    r = db.get(AssignableRole, role_id)
    if not r or r.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return r


def _assignment_out(db: Session, a: UserRoleAssignment) -> RoleAssignmentOut:
    u = db.get(User, a.user_id)
    r = db.get(AssignableRole, a.role_id)
    b = db.get(Branch, a.branch_id) if a.branch_id else None
    return RoleAssignmentOut(
        id=a.id, user_id=a.user_id, role_id=a.role_id, branch_id=a.branch_id,
        user_display_name=u.display_name if u else None,
        user_email=u.email if u else None,
        role_name=r.name if r else None,
        role_key=r.key if r else None,
        branch_name=b.name if b else None,
        created_at=a.created_at,
    )


@router.get("/{role_id}/assignees", response_model=list[RoleAssignmentOut])
def list_role_assignees(
    role_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _owned_role(db, role_id, user)
    rows = db.execute(
        select(UserRoleAssignment)
        .where(UserRoleAssignment.role_id == role_id)
        .order_by(UserRoleAssignment.id)
    ).scalars().all()
    return [_assignment_out(db, a) for a in rows]


@router.post("/{role_id}/assignees", response_model=RoleAssignmentOut, status_code=201)
def assign_role(
    role_id: int,
    payload: RoleAssignmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
):
    """指派角色給使用者。branch_id 為 null 代表全組織範圍。"""
    role = _owned_role(db, role_id, user)

    target = db.get(User, payload.user_id)
    if not target or target.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "使用者不存在")

    if payload.branch_id is not None:
        br = db.get(Branch, payload.branch_id)
        if not br or br.organization_id != user.organization_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "分公司不存在")

    # 不可指派超出自己管理範圍的職責；全組織範圍（null）需自身不受限
    if not in_branch_scope(db, user, payload.branch_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "指派範圍超出您的管理範圍（全組織範圍需 super admin）"
            if payload.branch_id is None else "該分公司不在您的管理範圍內",
        )

    # branch_id 可為 null，而 Postgres 視 NULL 互不相等，唯一約束擋不住重複，故顯式檢查
    dup = db.execute(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == payload.user_id,
            UserRoleAssignment.role_id == role_id,
            UserRoleAssignment.branch_id.is_(None) if payload.branch_id is None
            else UserRoleAssignment.branch_id == payload.branch_id,
        )
    ).scalar_one_or_none()
    if dup:
        raise HTTPException(status.HTTP_409_CONFLICT, "此使用者已被指派該角色與範圍")

    a = UserRoleAssignment(user_id=payload.user_id, role_id=role.id, branch_id=payload.branch_id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return _assignment_out(db, a)


@router.delete("/{role_id}/assignees/{assignment_id}", status_code=204)
def unassign_role(
    role_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
):
    _owned_role(db, role_id, user)
    a = db.get(UserRoleAssignment, assignment_id)
    if not a or a.role_id != role_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not in_branch_scope(db, user, a.branch_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "該指派不在您的管理範圍內")
    db.delete(a)
    db.commit()
