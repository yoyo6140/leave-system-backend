from datetime import datetime
from pydantic import BaseModel


class LeaveCreate(BaseModel):
    type:       str
    start_date: str
    end_date:   str
    hours:      int
    reason:     str = ""

class LeaveStatusUpdate(BaseModel):
    status:   str
    reviewer: str | None = None

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
