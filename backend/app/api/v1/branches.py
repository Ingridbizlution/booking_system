"""分支機構與地點。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import (
    Branch, Location, User, UserGroup, Resource, UserRoleAssignment,
)
from ...schemas import BranchOut, BranchCreate, BranchUpdate, LocationOut, LocationCreate
from ...core.rbac import branch_descendants, branch_scope, in_branch_scope
from ..deps import get_current_user, require_permission

router = APIRouter(prefix="/branches", tags=["organization"])


@router.get("", response_model=list[BranchOut])
def list_branches(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = select(Branch).where(Branch.organization_id == user.organization_id)
    scope = branch_scope(db, user)
    if scope is not None:
        q = q.where(Branch.id.in_(scope))
    return db.execute(q.order_by(Branch.id)).scalars().all()


@router.post("", response_model=BranchOut, status_code=201)
def create_branch(payload: BranchCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("resource"))):
    # 只能在自己範圍內的分公司底下建子分公司；建立頂層分公司需 super admin
    if not in_branch_scope(db, user, payload.parent_branch_id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "上層分公司不在您的管理範圍內（建立頂層分公司需 super admin）",
        )
    br = Branch(organization_id=user.organization_id, **payload.model_dump())
    db.add(br)
    db.commit()
    db.refresh(br)
    return br


def _owned_branch(db: Session, branch_id: int, user: User) -> Branch:
    br = db.get(Branch, branch_id)
    if not br or br.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if not in_branch_scope(db, user, branch_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return br


@router.patch("/{branch_id}", response_model=BranchOut)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    br = _owned_branch(db, branch_id, user)
    data = payload.model_dump(exclude_unset=True)

    if "parent_branch_id" in data:
        new_parent = data["parent_branch_id"]
        if new_parent is not None:
            parent = db.get(Branch, new_parent)
            if not parent or parent.organization_id != user.organization_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "上層分公司不存在")
            # 不可指向自己或自己的下層，否則階層會形成環、
            # 使 branch_descendants() 的走訪無法終止
            if new_parent in branch_descendants(db, branch_id):
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "不可將上層設為自己或自己的下層分公司",
                )
        if not in_branch_scope(db, user, new_parent):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "上層分公司不在您的管理範圍內")

    for k, v in data.items():
        setattr(br, k, v)
    db.commit()
    db.refresh(br)
    return br


@router.delete("/{branch_id}", status_code=204)
def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("resource")),
):
    """刪除分公司。

    仍有下層分公司、地點、資源、使用者或群組時一律拒絕：
    資料庫的 FK 是 CASCADE / SET NULL，直接刪會連帶清掉地點，並讓房間與設備
    變成無分公司歸屬的孤兒 —— 依物件層級權限規則，那些資料會對所有人隱形。
    """
    br = _owned_branch(db, branch_id, user)

    blockers: list[str] = []
    checks = [
        ("下層分公司", select(func.count(Branch.id)).where(Branch.parent_branch_id == branch_id)),
        ("地點", select(func.count(Location.id)).where(Location.branch_id == branch_id)),
        ("資源", select(func.count(Resource.id)).where(Resource.branch_id == branch_id)),
        ("使用者", select(func.count(User.id)).where(User.branch_id == branch_id)),
        ("群組", select(func.count(UserGroup.id)).where(UserGroup.branch_id == branch_id)),
        ("角色指派", select(func.count(UserRoleAssignment.id))
            .where(UserRoleAssignment.branch_id == branch_id)),
    ]
    for label, stmt in checks:
        n = db.execute(stmt).scalar_one() or 0
        if n:
            blockers.append(f"{label} {n} 筆")

    # 位於此分公司地點底下的資源（resource.branch_id 為空、靠 location 歸屬）
    via_loc = db.execute(
        select(func.count(Resource.id))
        .where(
            Resource.branch_id.is_(None),
            Resource.location_id.in_(select(Location.id).where(Location.branch_id == branch_id)),
        )
    ).scalar_one() or 0
    if via_loc:
        blockers.append(f"位於其地點下的資源 {via_loc} 筆")

    if blockers:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "此分公司仍有關聯資料，無法刪除：" + "、".join(blockers) + "。請先移除或轉移。",
        )

    db.delete(br)
    db.commit()


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
    scope = branch_scope(db, user)
    if scope is not None:
        q = q.where(Location.branch_id.in_(scope))
    return db.execute(q.order_by(Location.id)).scalars().all()


@loc_router.post("", response_model=LocationOut, status_code=201)
def create_location(payload: LocationCreate, db: Session = Depends(get_db), user: User = Depends(require_permission("resource"))):
    br = db.get(Branch, payload.branch_id)
    if not br or br.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "分支不存在")
    if not in_branch_scope(db, user, payload.branch_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "該分公司不在您的管理範圍內")
    loc = Location(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


def _owns_location(loc: Location, db: Session, user: User) -> bool:
    """地點須屬於同組織，且其分公司在使用者範圍內。"""
    br = db.get(Branch, loc.branch_id)
    if not br or br.organization_id != user.organization_id:
        return False
    return in_branch_scope(db, user, loc.branch_id)


@loc_router.patch("/{loc_id}", response_model=LocationOut)
def update_location(
    loc_id: int, payload: LocationCreate,
    db: Session = Depends(get_db), user: User = Depends(require_permission("resource")),
):
    loc = db.get(Location, loc_id)
    if not loc or not _owns_location(loc, db, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    # 若改分支，確認新分支也屬於同一組織且在管理範圍內
    new_br = db.get(Branch, payload.branch_id)
    if not new_br or new_br.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "分支不存在或不屬於您的組織")
    if not in_branch_scope(db, user, payload.branch_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "目標分公司不在您的管理範圍內")
    for k, v in payload.model_dump().items():
        setattr(loc, k, v)
    db.commit()
    db.refresh(loc)
    return loc


@loc_router.delete("/{loc_id}", status_code=204)
def delete_location(
    loc_id: int,
    db: Session = Depends(get_db), user: User = Depends(require_permission("resource")),
):
    loc = db.get(Location, loc_id)
    if not loc or not _owns_location(loc, db, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(loc)
    db.commit()
