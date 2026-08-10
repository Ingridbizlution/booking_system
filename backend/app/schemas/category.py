from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ---------- UserGroupCategory ----------
class UserGroupCategoryBase(BaseModel):
    key: str
    label: str
    icon: str = "ti-category"
    is_enabled: bool = True
    is_public_visible: bool = True


class UserGroupCategoryCreate(UserGroupCategoryBase):
    pass


class UserGroupCategoryUpdate(BaseModel):
    label: str | None = None
    icon: str | None = None
    is_enabled: bool | None = None
    is_public_visible: bool | None = None


class UserGroupCategoryOut(UserGroupCategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    group_count: int = 0
    created_at: datetime | None = None


# ---------- AssignableRole ----------
class AssignableRoleBase(BaseModel):
    name: str
    description: str | None = None
    icon: str = "ti-user-star"
    bound_group_id: int | None = None
    is_enabled: bool = True


class AssignableRoleCreate(AssignableRoleBase):
    pass


class AssignableRoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    icon: str | None = None
    bound_group_id: int | None = None
    is_enabled: bool | None = None


class AssignableRoleOut(AssignableRoleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    bound_group_name: str | None = None
    #: 內建職責識別碼（如 reservation_approver）；自訂角色為 null。唯讀。
    key: str | None = None
    assignee_count: int = 0
    created_at: datetime | None = None


# ---------- 角色指派 ----------
class RoleAssignmentIn(BaseModel):
    """指派角色給使用者。branch_id 為 null 代表全組織範圍。"""
    user_id: int
    branch_id: int | None = None


class RoleAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role_id: int
    branch_id: int | None = None
    # 便於前端顯示，避免額外查詢
    user_display_name: str | None = None
    user_email: str | None = None
    role_name: str | None = None
    role_key: str | None = None
    branch_name: str | None = None
    created_at: datetime | None = None
