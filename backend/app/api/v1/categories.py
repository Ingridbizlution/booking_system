"""用戶群組類別（Categories）。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import User, UserGroup, UserGroupCategory
from ...schemas import (
    UserGroupCategoryOut, UserGroupCategoryCreate, UserGroupCategoryUpdate,
)
from ..deps import get_current_user, require_permission

router = APIRouter(prefix="/categories", tags=["organization"])


def _to_out(c: UserGroupCategory, group_count: int = 0) -> UserGroupCategoryOut:
    return UserGroupCategoryOut(
        id=c.id,
        organization_id=c.organization_id,
        key=c.key,
        label=c.label,
        icon=c.icon,
        is_enabled=c.is_enabled,
        is_public_visible=c.is_public_visible,
        group_count=group_count,
        created_at=c.created_at,
    )


@router.get("", response_model=list[UserGroupCategoryOut])
def list_categories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """列出類別，同時統計每個類別底下有幾個 UserGroup（用 key 對照）。"""
    rows = db.execute(
        select(
            UserGroupCategory,
            func.count(UserGroup.id).label("group_count"),
        )
        .outerjoin(
            UserGroup,
            (UserGroup.category == UserGroupCategory.key)
            & (UserGroup.organization_id == UserGroupCategory.organization_id),
        )
        .where(UserGroupCategory.organization_id == user.organization_id)
        .group_by(UserGroupCategory.id)
        .order_by(UserGroupCategory.id)
    ).all()
    return [_to_out(c, cnt or 0) for c, cnt in rows]


@router.post("", response_model=UserGroupCategoryOut, status_code=201)
def create_category(
    payload: UserGroupCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
):
    exists = db.execute(
        select(UserGroupCategory).where(
            UserGroupCategory.organization_id == user.organization_id,
            UserGroupCategory.key == payload.key,
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "此類別 key 已存在")

    c = UserGroupCategory(organization_id=user.organization_id, **payload.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_out(c, 0)


@router.patch("/{cat_id}", response_model=UserGroupCategoryOut)
def update_category(
    cat_id: int,
    payload: UserGroupCategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
):
    c = db.get(UserGroupCategory, cat_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    for k, v in payload.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(c, k, v)
    db.commit()
    db.refresh(c)
    cnt = db.execute(
        select(func.count(UserGroup.id)).where(
            UserGroup.organization_id == user.organization_id,
            UserGroup.category == c.key,
        )
    ).scalar_one() or 0
    return _to_out(c, cnt)


@router.delete("/{cat_id}", status_code=204)
def delete_category(
    cat_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("user")),
):
    c = db.get(UserGroupCategory, cat_id)
    if not c or c.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # 若仍有群組使用此 key，禁止刪除
    in_use = db.execute(
        select(func.count(UserGroup.id)).where(
            UserGroup.organization_id == user.organization_id,
            UserGroup.category == c.key,
        )
    ).scalar_one() or 0
    if in_use:
        raise HTTPException(status.HTTP_409_CONFLICT, f"仍有 {in_use} 個群組使用此類別")
    db.delete(c)
    db.commit()
