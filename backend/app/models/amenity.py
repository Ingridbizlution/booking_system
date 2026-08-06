"""附屬設備（Amenity）模型 — 可連結至房間、設備等可預約資源的附加屬性。"""
from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base, TimestampMixin


class Amenity(Base, TimestampMixin):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    icon: Mapped[str] = mapped_column(String(60), default="box")
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))


class ResourceAmenity(Base):
    """附屬設備與資源之間的多對多關聯。"""
    __tablename__ = "resource_amenities"

    id: Mapped[int] = mapped_column(primary_key=True)
    amenity_id: Mapped[int] = mapped_column(ForeignKey("amenities.id", ondelete="CASCADE"))
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
