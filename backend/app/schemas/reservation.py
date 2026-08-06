from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReservationBase(BaseModel):
    resource_id: int
    title: str = Field(min_length=1, max_length=200)
    start_at: datetime
    end_at: datetime
    type: str = "normal"
    notes: str | None = None


class ReservationCreate(ReservationBase):
    attendee_user_ids: list[int] = []
    attendee_external_emails: list[str] = []


class ReservationUpdate(BaseModel):
    title: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    notes: str | None = None
    resource_id: int | None = None
    type: str | None = None
    attendee_user_ids: list[int] | None = None


class ReservationApproveIn(BaseModel):
    approve: bool = True
    note: str | None = None


class AttendeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    external_email: str | None
    response: str


class ReservationOut(ReservationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    organizer_id: int
    status: str
    approved_by: int | None
    check_in_at: datetime | None
    created_at: datetime
    organizer_name: str | None = None
    resource_name: str | None = None
    attendees: list[AttendeeOut] = []
    access_code: str | None = None


class DashboardStats(BaseModel):
    resource_count: int
    reservation_count: int
    total_hours: float
    utilization_rate: float  # 0..1
    total_available_hours: float
    daily_hours: list[dict]  # [{date, hours}]
    by_type: dict           # {normal, recurring, walk_in}
    by_duration: dict       # {"<=30": n, "30-60": n, ...}
