from pydantic import BaseModel


class PendingLeaveItem(BaseModel):
    id:         str
    user_id:    int
    user_name:  str
    type:       str
    hours:      int
    start_date: str
    end_date:   str
    created_at: str


class TopLeaveHoursItem(BaseModel):
    user_id: int
    name:    str
    hours:   int


class OverviewData(BaseModel):
    pending_count:       int
    approved_this_month: int
    employee_count:      int
    pending_list:        list[PendingLeaveItem]
    top_leave_hours:     list[TopLeaveHoursItem]


class OverviewResponse(BaseModel):
    success: bool = True
    data:    OverviewData
