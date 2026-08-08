from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoomBase(BaseModel):
    name: str
    capacity: int = 0
    category: str | None = None
    location_id: int | None = None
    subtype: str = "standard"  # standard / combinable
    image_url: str | None = None
    status: str = "available"
    description: str | None = None
    branch_id: int | None = None
    combined_room_ids: list[int] = []
    team_space: bool = False
    requires_approval: bool = True
    priority: int = 0
    booking_policy_id: int | None = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None
    category: str | None = None
    location_id: int | None = None
    subtype: str | None = None
    image_url: str | None = None
    status: str | None = None
    description: str | None = None
    branch_id: int | None = None
    combined_room_ids: list[int] | None = None
    team_space: bool | None = None
    requires_approval: bool | None = None
    priority: int | None = None
    booking_policy_id: int | None = None


class RoomOut(RoomBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    type: str
    qr_code: str | None
    location_name: str | None = None
    branch_name: str | None = None
    combined_room_names: list[str] = []


# ---- 暫停服務時間 (Blackout) ----
class BlackoutBase(BaseModel):
    start_at: datetime
    end_at: datetime
    block_reservations: bool = True
    public_note: str | None = None
    internal_note: str | None = None


class BlackoutCreate(BlackoutBase):
    pass


class BlackoutOut(BlackoutBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    resource_id: int
    created_at: datetime
