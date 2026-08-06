from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AmenityCreate(BaseModel):
    name: str
    icon: str = "box"
    branch_id: int | None = None


class AmenityUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    branch_id: int | None = None


class AmenityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    name: str
    icon: str
    branch_id: int | None = None
    branch_name: str | None = None
    created_at: datetime
    updated_at: datetime
    room_ids: list[int] = []
    desk_ids: list[int] = []
    equipment_ids: list[int] = []
    parking_ids: list[int] = []
    other_ids: list[int] = []


class ResourceAmenityIn(BaseModel):
    resource_ids: list[int]
