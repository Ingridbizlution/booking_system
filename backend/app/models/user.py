"""用戶 / 群組模型。"""
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, UniqueConstraint, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # active/pending/disabled
    password_hash: Mapped[str | None] = mapped_column(Text)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 個人資料欄位（Drawer 使用）
    title: Mapped[str | None] = mapped_column(String(120))              # 職稱
    department: Mapped[str | None] = mapped_column(String(120))         # 部門
    employee_id: Mapped[str | None] = mapped_column(String(60))         # 員工編號
    phone: Mapped[str | None] = mapped_column(String(40))               # 電話號碼
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    delegate_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    mfa_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    # 使用者個人權限（區別於群組權限）；格式：
    # { "ui_access": true, "is_super_admin": false,
    #   "admin": {"reservation": {"read": true, "write": false}, ...} }
    permissions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    groups: Mapped[list["UserGroup"]] = relationship(
        secondary="user_group_members", back_populates="members"
    )


class UserGroup(Base, TimestampMixin):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(60), default="general")  # 對照 user_group_categories.key
    description: Mapped[str | None] = mapped_column(Text)
    # 分支機構歸屬（NULL = 組織全域）
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    # 管理控制台存取權限；格式：{"reservation_manager": {"read": bool, "write": bool}, ...}
    permissions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    members: Mapped[list[User]] = relationship(
        secondary="user_group_members", back_populates="groups"
    )


class UserGroupMember(Base):
    __tablename__ = "user_group_members"
    __table_args__ = (UniqueConstraint("user_id", "group_id", name="uq_user_group"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    group_id: Mapped[int] = mapped_column(ForeignKey("user_groups.id", ondelete="CASCADE"))
