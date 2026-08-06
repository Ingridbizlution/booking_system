"""用戶與用戶群組。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import User, UserGroup, UserGroupMember, Branch
from ...core.security import hash_password
from ...schemas import (
    UserOut, UserDetail, UserCreate, UserUpdate,
    UserGroupOut, UserGroupCreate, UserGroupUpdate, GroupMemberIn,
)
from ..deps import get_current_user

router = APIRouter(prefix="/users", tags=["organization"])


def _to_user_out(db: Session, u: User) -> UserOut:
    branch_name = db.get(Branch, u.branch_id).name if u.branch_id else None
    delegate_name = None
    if u.delegate_user_id:
        d = db.get(User, u.delegate_user_id)
        delegate_name = d.display_name if d else None
    return UserOut(
        id=u.id, organization_id=u.organization_id,
        email=u.email, display_name=u.display_name, avatar_url=u.avatar_url,
        status=u.status, last_login_at=u.last_login_at, created_at=u.created_at,
        title=u.title, department=u.department, employee_id=u.employee_id, phone=u.phone,
        branch_id=u.branch_id, branch_name=branch_name,
        delegate_user_id=u.delegate_user_id, delegate_name=delegate_name,
        mfa_enabled=u.mfa_enabled,
        permissions=u.permissions or {},
    )


@router.get("", response_model=list[UserOut])
def list_users(
    q: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(User).where(User.organization_id == user.organization_id)
    if q:
        stmt = stmt.where(User.display_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    users = db.execute(stmt.order_by(User.id)).scalars().all()
    return [_to_user_out(db, u) for u in users]


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    exists = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "此電子郵件已存在")

    new = User(
        organization_id=user.organization_id,
        email=payload.email,
        display_name=payload.display_name,
        avatar_url=payload.avatar_url,
        status="active" if payload.password else "pending",
        password_hash=hash_password(payload.password) if payload.password else None,
    )
    db.add(new)
    db.flush()

    for gid in payload.group_ids:
        g = db.get(UserGroup, gid)
        if g and g.organization_id == user.organization_id:
            db.add(UserGroupMember(user_id=new.id, group_id=gid))
    db.commit()
    db.refresh(new)
    return _to_user_out(db, new)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    target = db.get(User, user_id)
    if not target or target.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    # 個人資料 / 狀態欄位
    simple = ["display_name", "avatar_url", "status",
              "title", "department", "employee_id", "phone",
              "branch_id", "delegate_user_id", "mfa_enabled", "permissions"]
    for k in simple:
        v = getattr(payload, k, None)
        if v is not None:
            setattr(target, k, v)

    if payload.group_ids is not None:
        db.query(UserGroupMember).filter(UserGroupMember.user_id == target.id).delete()
        for gid in payload.group_ids:
            g = db.get(UserGroup, gid)
            if g and g.organization_id == user.organization_id:
                db.add(UserGroupMember(user_id=target.id, group_id=gid))

    db.commit()
    db.refresh(target)
    return _to_user_out(db, target)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _to_user_out(db, user)


@router.get("/{user_id}", response_model=UserDetail)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """回傳單一用戶完整資料（Drawer 用），附上所屬群組清單。"""
    target = db.get(User, user_id)
    if not target or target.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    base = _to_user_out(db, target)
    # 附上群組清單（含 branch_name 與 permissions；沿用 _to_group_out）
    rows = db.execute(
        select(
            UserGroup,
            func.count(UserGroupMember.id).label("member_count"),
        )
        .join(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
        .where(UserGroupMember.user_id == target.id)
        .group_by(UserGroup.id)
        .order_by(UserGroup.id)
    ).all()
    groups_out = [_to_group_out(g, cnt or 0, _branch_name(db, g.branch_id)) for g, cnt in rows]

    return UserDetail(**base.model_dump(), groups=groups_out)


# ---------------- Groups ----------------
group_router = APIRouter(prefix="/groups", tags=["organization"])


@group_router.get("", response_model=list[UserGroupOut])
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(
        select(
            UserGroup,
            func.count(UserGroupMember.id).label("member_count"),
        )
        .outerjoin(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
        .where(UserGroup.organization_id == user.organization_id)
        .group_by(UserGroup.id)
        .order_by(UserGroup.id)
    ).all()
    return [_to_group_out(g, cnt or 0, _branch_name(db, g.branch_id)) for g, cnt in rows]


def _to_group_out(g: UserGroup, member_count: int = 0, branch_name: str | None = None) -> UserGroupOut:
    return UserGroupOut(
        id=g.id,
        organization_id=g.organization_id,
        name=g.name,
        category=g.category,
        description=g.description,
        branch_id=g.branch_id,
        branch_name=branch_name,
        permissions=g.permissions or {},
        member_count=member_count,
        created_at=g.created_at,
        updated_at=g.updated_at,
    )


def _branch_name(db: Session, bid: int | None) -> str | None:
    if not bid:
        return None
    b = db.get(Branch, bid)
    return b.name if b else None


@group_router.get("/{group_id}", response_model=UserGroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    cnt = db.execute(
        select(func.count(UserGroupMember.id)).where(UserGroupMember.group_id == group_id)
    ).scalar_one() or 0
    return _to_group_out(g, cnt, _branch_name(db, g.branch_id))


@group_router.get("/{group_id}/members", response_model=list[UserOut])
def list_group_members(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    users = db.execute(
        select(User).join(UserGroupMember, UserGroupMember.user_id == User.id)
        .where(UserGroupMember.group_id == group_id)
        .order_by(User.id)
    ).scalars().all()
    return users


@group_router.post("", response_model=UserGroupOut, status_code=201)
def create_group(payload: UserGroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    g = UserGroup(organization_id=user.organization_id, **payload.model_dump())
    db.add(g)
    db.commit()
    db.refresh(g)
    return _to_group_out(g, 0, _branch_name(db, g.branch_id))


@group_router.patch("/{group_id}", response_model=UserGroupOut)
def update_group(
    group_id: int, payload: UserGroupUpdate,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(g, k, v)
    db.commit()
    db.refresh(g)
    cnt = db.execute(
        select(func.count(UserGroupMember.id)).where(UserGroupMember.group_id == group_id)
    ).scalar_one() or 0
    return _to_group_out(g, cnt, _branch_name(db, g.branch_id))


@group_router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(g)
    db.commit()


@group_router.delete("/{group_id}/members/{user_id}", status_code=204)
def remove_member(
    group_id: int, user_id: int,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    m = db.execute(
        select(UserGroupMember).where(
            UserGroupMember.group_id == group_id,
            UserGroupMember.user_id == user_id,
        )
    ).scalar_one_or_none()
    if m:
        db.delete(m)
        db.commit()


@group_router.post("/{group_id}/members", status_code=204)
def add_members(
    group_id: int,
    payload: GroupMemberIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    g = db.get(UserGroup, group_id)
    if not g or g.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for uid in payload.user_ids:
        u = db.get(User, uid)
        if u and u.organization_id == user.organization_id:
            exists = db.execute(
                select(UserGroupMember).where(
                    UserGroupMember.user_id == uid,
                    UserGroupMember.group_id == group_id,
                )
            ).scalar_one_or_none()
            if not exists:
                db.add(UserGroupMember(user_id=uid, group_id=group_id))
    db.commit()
