"""組織 / 分支 / 地點模型。"""
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Taipei", nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="zh-TW", nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(String(20), default="trial")

    branches: Mapped[list["Branch"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Branch(Base, TimestampMixin):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Taipei")
    # 分支階層：例如 台北分公司 / 新竹分公司 的 parent = HQ
    parent_branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))

    organization: Mapped[Organization] = relationship(back_populates="branches")
    locations: Mapped[list["Location"]] = relationship(back_populates="branch", cascade="all, delete-orphan")


class Location(Base, TimestampMixin):
    """地點 / 建築 / 樓層，樹狀結構。"""
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_id: Mapped[int] = mapped_column(ForeignKey("branches.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(20), default="floor")  # building / floor / area
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    floor_plan_url: Mapped[str | None] = mapped_column(Text)

    branch: Mapped[Branch] = relationship(back_populates="locations")
    parent: Mapped["Location | None"] = relationship(remote_side="Location.id")
