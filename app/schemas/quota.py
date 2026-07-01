from datetime import date
from pydantic import BaseModel


class QuotaItem(BaseModel):
    type:            str
    total_days:      int | None
    total_hours:     int | None
    used_hours:      int = 0
    remaining_hours: int | None = None
    note:            str | None = None


class LeaveQuotaOut(BaseModel):
    user_id:    int
    username:   str
    name:       str
    as_of:      date
    year_start: date
    year_end:   date
    quotas:     list[QuotaItem]

class LeaveQuotaResponse(BaseModel):
    success: bool = True
    data: LeaveQuotaOut
