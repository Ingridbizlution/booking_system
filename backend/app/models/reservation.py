"""預約模型。"""
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.base import Base, TimestampMixin


class Reservation(Base, TimestampMixin):
    __tablename__ = "reservations"
    __table_args__ = (
        Index("ix_resv_resource_time", "resource_id", "start_at", "end_at"),
        Index("ix_resv_organizer", "organizer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="normal")  # normal / recurring / walk_in
    status: Mapped[str] = mapped_column(String(20), default="approved")
    # pending / approved / rejected / cancelled / checked_in / no_show
    recurrence_rule: Mapped[str | None] = mapped_column(Text)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    notes: Mapped[str | None] = mapped_column(Text)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_code: Mapped[str | None] = mapped_column(String(10), index=True)  # 6 位隨機數字

    attendees: Mapped[list["ReservationAttendee"]] = relationship(
        back_populates="reservation", cascade="all, delete-orphan"
    )


class ReservationAttendee(Base):
    __tablename__ = "reservation_attendees"

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id", ondelete="CASCADE"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    external_email: Mapped[str | None] = mapped_column(String(255))
    response: Mapped[str] = mapped_column(String(20), default="pending")

    reservation: Mapped[Reservation] = relationship(back_populates="attendees")
