from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict

from .category import RoleAssignmentOut


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    avatar_url: str | None = None


class UserCreate(UserBase):
    password: str | None = None  # None = 走邀請流程
    group_ids: list[int] = []


class UserUpdate(BaseModel):
    """一般欄位更新。

    注意：`permissions` 刻意不在此處 —— 權限變更必須走
    `PUT /users/{id}/permissions`，該端點有獨立的授權守衛。
    以 extra="forbid" 讓誤傳 `permissions` 直接得到 422，而非靜默忽略。
    """
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    avatar_url: str | None = None
    status: str | None = None
    group_ids: list[int] | None = None
    title: str | None = None
    department: str | None = None
    employee_id: str | None = None
    phone: str | None = None
    branch_id: int | None = None
    delegate_user_id: int | None = None
    mfa_enabled: bool | None = None


class UserPermissionsUpdate(BaseModel):
    """權限變更專用；僅 `PUT /users/{id}/permissions` 使用。"""
    ui_access: bool = True
    is_super_admin: bool = False
    admin: dict[str, dict[str, bool]] = {}


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    status: str
    last_login_at: datetime | None
    created_at: datetime
    # v3.2 新增個人資料欄位
    title: str | None = None
    department: str | None = None
    employee_id: str | None = None
    phone: str | None = None
    branch_id: int | None = None
    branch_name: str | None = None
    delegate_user_id: int | None = None
    delegate_name: str | None = None
    mfa_enabled: bool = False
    permissions: dict = {}


class MeOut(UserOut):
    """`GET /users/me` 專用：附上解析後的有效權限。

    `permissions` 只是本人的直接授權；真正的權限還包含群組繼承與 admin 群組的
    全域權，前端無法自行推導，因此由後端解析後提供。刻意不放進 `UserOut`，
    避免列表端點為每個使用者重複查詢群組。
    """
    #: 合併個人授權與群組繼承後的結果：{module: {"read": bool, "write": bool}}
    effective_permissions: dict[str, dict[str, bool]] = {}
    #: 全域管理員（super admin 或屬於 category='admin' 的群組）
    is_admin: bool = False
    is_super_admin: bool = False
    #: 是否可進入管理控制台
    ui_access: bool = True
    #: 可存取的分公司 ID；None = 不受限
    branch_scope: list[int] | None = None


class UserDetail(UserOut):
    """Drawer 用；額外附上群組與角色指派清單，避免前端逐筆查詢。"""
    groups: list["UserGroupOut"] = []
    roles: list[RoleAssignmentOut] = []


class UserGroupBase(BaseModel):
    name: str
    category: str = "general"
    description: str | None = None
    branch_id: int | None = None
    permissions: dict = {}  # {"reservation_manager": {"read": true, "write": false}, ...}


class UserGroupCreate(UserGroupBase):
    pass


class UserGroupUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    branch_id: int | None = None
    permissions: dict | None = None


class UserGroupOut(UserGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    branch_name: str | None = None
    member_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GroupMemberIn(BaseModel):
    user_ids: list[int]
