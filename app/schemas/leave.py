from datetime import datetime
from pydantic import BaseModel


class LeaveStatusLogOut(BaseModel):
    id:          str
    from_status: str | None
    to_status:   str
    changed_by:  int
    changed_at:  datetime

    model_config = {"from_attributes": True}


class LeaveCreate(BaseModel):
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str = ""

class LeaveUpdate(BaseModel):
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str = ""

class LeaveStatusUpdate(BaseModel):
    status: str

class LeaveOut(BaseModel):
    id:         str
    user_id:    int
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str
    status:     str
    reviewer:   str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

class LeaveListData(BaseModel):
    total: int
    page:  int
    limit: int
    data:  list[LeaveOut]

class LeaveListResponse(BaseModel):
    success: bool = True
    data: LeaveListData

class LeaveResponse(BaseModel):
    success: bool = True
    data: LeaveOut

class LeaveStatusLogListResponse(BaseModel):
    success: bool = True
    data: list[LeaveStatusLogOut]
