from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    display_name: str
    avatar_url: str | None = None


class UserCreate(UserBase):
    password: str | None = None  # None = 走邀請流程
    group_ids: list[int] = []


class UserUpdate(BaseModel):
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
    permissions: dict | None = None


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


class UserDetail(UserOut):
    """Drawer 用；額外附上群組清單。"""
    groups: list["UserGroupOut"] = []


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
