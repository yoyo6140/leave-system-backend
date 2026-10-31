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


class OverviewData(BaseModel):
    pending_count:       int
    approved_this_month: int
    employee_count:      int
    pending_list:        list[PendingLeaveItem]


class OverviewResponse(BaseModel):
    success: bool = True
    data:    OverviewData


class MonthlyLeaveStatItem(BaseModel):
    month: int  # 1~12
    count: int  # 該月已通過的請假次數（依 start_date 歸屬）


class MonthlyLeaveStatsData(BaseModel):
    year:   int
    months: list[MonthlyLeaveStatItem]  # 固定 12 筆，1~12 月都有，沒有資料就是 0


class MonthlyLeaveStatsResponse(BaseModel):
    success: bool = True
    data:    MonthlyLeaveStatsData
