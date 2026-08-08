"""資源模型（第一輪只用 type='room'）。"""
from datetime import datetime
from sqlalchemy import String, ForeignKey, Integer, Text, JSON, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from ..db.base import Base, TimestampMixin


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column(String(20), default="room")  # room / desk / equipment / parking / other
    subtype: Mapped[str | None] = mapped_column(String(20))  # standard / combinable
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str | None] = mapped_column(String(60))
    image_url: Mapped[str | None] = mapped_column(Text)
    qr_code: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="available")
    attributes: Mapped[dict | None] = mapped_column(JSON, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"))
    # 可合併房間才會用到：組成此房間的來源房間 ID 清單
    combined_room_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    # 規則
    team_space: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 政策：預設每間會議室都需要審批（可在房間規則 tab 關閉）
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    booking_policy_id: Mapped[int | None] = mapped_column(ForeignKey("booking_policies.id", ondelete="SET NULL"))
    # 建議優先級 0-5
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ResourceBlackout(Base, TimestampMixin):
    """暫停服務時間：資源在特定時段內不可預約（維修/保養）。"""
    __tablename__ = "resource_blackouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resources.id", ondelete="CASCADE"))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    block_reservations: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    public_note: Mapped[str | None] = mapped_column(Text)      # 顯示給使用者的備註
    internal_note: Mapped[str | None] = mapped_column(Text)    # 僅管理者可見
