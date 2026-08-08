"""審核規則（BookingPolicy）模型。"""
from sqlalchemy import String, ForeignKey, Integer, Boolean, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin


class BookingPolicy(Base, TimestampMixin):
    __tablename__ = "booking_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    lock_slot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    conditional_mode: Mapped[str] = mapped_column(String(20), default="all")
    conditions: Mapped[list | None] = mapped_column(JSON, default=list)
    re_approve_mode: Mapped[str] = mapped_column(String(20), default="always")
    show_approver: Mapped[str] = mapped_column(String(20), default="hide")
    auto_reject_days: Mapped[int] = mapped_column(Integer, default=7)

    approvers: Mapped[list["BookingPolicyApprover"]] = relationship(
        back_populates="policy", cascade="all, delete-orphan"
    )


class BookingPolicyApprover(Base):
    __tablename__ = "booking_policy_approvers"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_policy_id: Mapped[int] = mapped_column(ForeignKey("booking_policies.id", ondelete="CASCADE"))
    approver_type: Mapped[str] = mapped_column(String(10), nullable=False)
    approver_id: Mapped[int] = mapped_column(Integer, nullable=False)

    policy: Mapped[BookingPolicy] = relationship(back_populates="approvers")
