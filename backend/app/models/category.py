"""用戶群組類別 + 可指派角色。

設計原則（相容性）：
- UserGroup.category 目前是 String key（'admin' / 'support' / 'general' / …），
  改為 FK 會破壞既有前端。這裡改用 `key` 欄位對照 UserGroup.category，
  seed 時把所有既有 key 都建為 UserGroupCategory 一筆，之後可管理化。
"""
from sqlalchemy import String, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base, TimestampMixin


class UserGroupCategory(Base, TimestampMixin):
    __tablename__ = "user_group_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_ugcat_org_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(60), nullable=False)  # 對應 UserGroup.category
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="ti-category")
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_public_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AssignableRole(Base, TimestampMixin):
    """可指派角色 —— 職責型，非權限型。可選綁定一個 UserGroup 用於暫時授權。"""
    __tablename__ = "assignable_roles"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_role_org_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(60), default="ti-user-star")
    bound_group_id: Mapped[int | None] = mapped_column(ForeignKey("user_groups.id", ondelete="SET NULL"))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
