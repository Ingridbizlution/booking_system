from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    timezone: str
    locale: str
    plan: str


class BranchBase(BaseModel):
    name: str
    address: str | None = None
    timezone: str = "Asia/Taipei"
    parent_branch_id: int | None = None


class BranchCreate(BranchBase):
    pass


class BranchOut(BranchBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    organization_id: int
    created_at: datetime


class LocationBase(BaseModel):
    branch_id: int
    parent_id: int | None = None
    type: str = "floor"
    name: str
    floor_plan_url: str | None = None


class LocationCreate(LocationBase):
    pass


class LocationOut(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
