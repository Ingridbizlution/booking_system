"""RBAC 權限解析。

權限資料有兩處來源，兩者聯集構成使用者的有效權限：

1. ``User.permissions``（個人直接授權）::

       {"ui_access": true, "is_super_admin": false,
        "admin": {"reservation": {"read": true, "write": false}, ...}}

2. ``UserGroup.permissions``（透過群組繼承）::

       {"reservation": {"read": true, "write": false}, ...}

另外 ``category == "admin"`` 的群組視為該組織的全域管理員（沿用 seed 的
「系統管理員」群組設定，其 permissions JSON 為空但應具備全部權限）。

權限（能做什麼）與範圍（能對哪些分公司做）是兩個獨立維度，寫入操作必須
兩者皆通過：``has_permission()`` 判斷前者，``branch_scope()`` 判斷後者。
"""
from sqlalchemy import and_, false, or_, select
from sqlalchemy.orm import Session

from ..models import (
    AssignableRole, Branch, Location, Resource, User, UserGroup, UserGroupMember,
    UserRoleAssignment,
)

#: 管理控制台的 14 個模組（與前端 org-groups.html 的 PERMISSIONS 一致）
MODULES = frozenset({
    "reservation", "resource", "service", "support", "visitor", "panel",
    "access", "event", "av", "mail", "workflow", "expense", "counter", "user",
})

#: write 隱含 read
ACTIONS = ("read", "write")


def is_super_admin(user: User) -> bool:
    return bool((user.permissions or {}).get("is_super_admin"))


def user_groups(db: Session, user: User) -> list[UserGroup]:
    return list(db.execute(
        select(UserGroup)
        .join(UserGroupMember, UserGroupMember.group_id == UserGroup.id)
        .where(UserGroupMember.user_id == user.id)
    ).scalars().all())


def role_assignments(db: Session, user: User) -> list[tuple[UserRoleAssignment, AssignableRole]]:
    """使用者目前有效的角色指派（僅含已啟用的角色）。"""
    return list(db.execute(
        select(UserRoleAssignment, AssignableRole)
        .join(AssignableRole, AssignableRole.id == UserRoleAssignment.role_id)
        .where(
            UserRoleAssignment.user_id == user.id,
            AssignableRole.is_enabled.is_(True),
        )
    ).all())


def holds_role(db: Session, user: User, role_key: str, branch_id: int | None = None) -> bool:
    """是否持有某 key 的角色；給定 branch_id 時，該分公司須落在指派範圍內。

    指派的 `branch_id` 為 null 代表全組織；否則涵蓋該分公司及其下層。
    """
    for assignment, role in role_assignments(db, user):
        if role.key != role_key:
            continue
        if branch_id is None or assignment.branch_id is None:
            return True
        if branch_id in branch_descendants(db, assignment.branch_id):
            return True
    return False


def is_admin_user(db: Session, user: User) -> bool:
    """管理員：super admin、屬於 category='admin' 的群組，或被指派了綁定該類群組的角色。

    注意：把角色綁定到 admin 類群組，等同讓被指派者在其指派範圍內成為管理員
    （範圍由 ``UserRoleAssignment.branch_id`` 限制，見 ``branch_scope``）。
    若只想給部分權限，請把角色綁到權限較窄的群組。
    """
    if is_super_admin(user):
        return True
    if any(g.category == "admin" for g in user_groups(db, user)):
        return True
    for _assignment, role in role_assignments(db, user):
        if role.bound_group_id:
            bound = db.get(UserGroup, role.bound_group_id)
            if bound and bound.category == "admin":
                return True
    return False


def effective_permissions(db: Session, user: User) -> dict[str, dict[str, bool]]:
    """回傳 {module: {"read": bool, "write": bool}}。

    來源三處聯集：個人授權、群組繼承、角色指派所綁定的群組。
    全域管理員視為對全部模組具備讀寫權，這樣此函式的結果才真正等同
    「這個人實際能做什麼」，可直接交給前端判斷 UI 顯示。
    """
    if is_admin_user(db, user):
        return {m: {"read": True, "write": True} for m in sorted(MODULES)}

    merged: dict[str, dict[str, bool]] = {}

    def absorb(source: dict | None):
        for module, flags in (source or {}).items():
            if module not in MODULES or not isinstance(flags, dict):
                continue
            cur = merged.setdefault(module, {"read": False, "write": False})
            for action in ACTIONS:
                if flags.get(action):
                    cur[action] = True

    absorb((user.permissions or {}).get("admin"))
    for g in user_groups(db, user):
        absorb(g.permissions)
    # 角色指派：綁定群組者，在指派存續期間取得該群組的權限
    for _assignment, role in role_assignments(db, user):
        if role.bound_group_id:
            bound = db.get(UserGroup, role.bound_group_id)
            if bound and bound.organization_id == user.organization_id:
                absorb(bound.permissions)

    # write 隱含 read
    for flags in merged.values():
        if flags["write"]:
            flags["read"] = True
    return merged


def has_permission(db: Session, user: User, module: str, action: str = "write") -> bool:
    if module not in MODULES:
        raise ValueError(f"unknown module: {module}")
    if is_admin_user(db, user):
        return True
    flags = effective_permissions(db, user).get(module)
    return bool(flags and flags.get(action))


# ---------------- 分公司範圍（物件層級權限） ----------------

def branch_descendants(db: Session, branch_id: int) -> set[int]:
    """回傳 branch_id 及其所有下層分公司（含自身）。"""
    seen = {branch_id}
    frontier = [branch_id]
    while frontier:
        rows = db.execute(
            select(Branch.id).where(Branch.parent_branch_id.in_(frontier))
        ).scalars().all()
        fresh = [r for r in rows if r not in seen]
        seen.update(fresh)
        frontier = fresh
    return seen


def branch_scope(db: Session, user: User) -> set[int] | None:
    """使用者可存取的分公司 ID 集合；``None`` 表示不受限（super admin）。

    範圍 = ``User.branch_id`` 的子樹 ∪ 各群組 ``branch_id`` 的子樹
           ∪ 各角色指派 ``branch_id`` 的子樹。

    群組的 ``branch_id`` 為 null 代表「非分公司限定的群組」（例如 seed 的
    「系統管理員」「一般員工」），只決定能做什麼、不放大能管哪裡，因此不貢獻
    範圍。要讓某人跨分公司管理，請把群組指定到上層分公司，或設為 super admin。

    角色指派的 ``branch_id`` 則是指派時明確選定的職責範圍，因此 null 在此代表
    「全組織」—— 與群組的 null 語意不同。

    因此位於根分公司（HQ）的使用者，其子樹自然涵蓋全組織；而台北分公司的
    管理員即使屬於 admin 群組，範圍仍只有台北及其下層。
    """
    if is_super_admin(user):
        return None
    scope: set[int] = set()
    if user.branch_id:
        scope |= branch_descendants(db, user.branch_id)
    for g in user_groups(db, user):
        if g.branch_id:
            scope |= branch_descendants(db, g.branch_id)
    for assignment, _role in role_assignments(db, user):
        if assignment.branch_id is None:
            return None      # 指派為全組織範圍
        scope |= branch_descendants(db, assignment.branch_id)
    return scope


def in_branch_scope(db: Session, user: User, branch_id: int | None) -> bool:
    """branch_id 是否在使用者範圍內。未指派分公司的物件僅 super admin 可存取。"""
    scope = branch_scope(db, user)
    if scope is None:
        return True
    return branch_id is not None and branch_id in scope


def resource_branch_id(db: Session, resource: Resource) -> int | None:
    """資源所屬分公司：直接指派優先，否則由 location 反推。"""
    if resource.branch_id:
        return resource.branch_id
    if resource.location_id:
        loc = db.get(Location, resource.location_id)
        if loc:
            return loc.branch_id
    return None


def can_access_resource(db: Session, user: User, resource: Resource) -> bool:
    return in_branch_scope(db, user, resource_branch_id(db, resource))


def resource_scope_clause(db: Session, user: User):
    """可直接放入 ``select().where()`` 的資源範圍條件；``None`` 表示不需過濾。"""
    scope = branch_scope(db, user)
    if scope is None:
        return None
    if not scope:
        return false()  # 未指派分公司且無群組範圍 → 看不到任何資源
    return or_(
        Resource.branch_id.in_(scope),
        and_(
            Resource.branch_id.is_(None),
            Resource.location_id.in_(
                select(Location.id).where(Location.branch_id.in_(scope))
            ),
        ),
    )
