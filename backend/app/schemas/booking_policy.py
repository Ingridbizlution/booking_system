from pydantic import BaseModel, ConfigDict, Field


class ApproverIn(BaseModel):
    type: str = Field(pattern=r"^(user|group)$")
    id: int


class ApproverOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    approver_type: str
    approver_id: int


class BookingPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lock_slot: bool = False
    conditional_mode: str = "all"
    conditions: list[str] = []
    re_approve_mode: str = "always"
    show_approver: str = "hide"
    approvers: list[ApproverIn] = []
    auto_reject_days: int = 7


class BookingPolicyUpdate(BaseModel):
    name: str | None = None
    lock_slot: bool | None = None
    conditional_mode: str | None = None
    conditions: list[str] | None = None
    re_approve_mode: str | None = None
    show_approver: str | None = None
    approvers: list[ApproverIn] | None = None
    auto_reject_days: int | None = None


class BookingPolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    name: str
    lock_slot: bool
    conditional_mode: str
    conditions: list[str]
    re_approve_mode: str
    show_approver: str
    auto_reject_days: int
    approvers: list[ApproverOut] = []
    created_at: str | None = None
    updated_at: str | None = None
