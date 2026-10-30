"""
台灣勞基法假別額度計算

特休（勞基法第 38 條）依年資計算；病假、事假為固定年度額度；
婚假、喪假、公假、其他無上限，由審核人自行判斷。
所有天數皆轉換為小時（1 天 = 8 小時）。
年度以「到職週年日」為基準重置。

假別本身（quota_type／quota_hours）存在 `leave_types` 表，不在這裡寫死，
呼叫端（app/routers/quota.py）要先查出 LeaveType 清單再傳進來。
"""

from datetime import date, timedelta
from typing import Protocol

HOURS_PER_DAY = 8


class LeaveTypeLike(Protocol):
    """只需要這三個欄位，方便測試時不用真的建 LeaveType ORM 物件"""
    code: str
    quota_type: str
    quota_hours: int | None


def calc_seniority_months(hire_date: date, as_of: date) -> tuple[int, int]:
    """回傳 (完整年數, 扣除整年後的月數)"""
    years  = as_of.year  - hire_date.year
    months = as_of.month - hire_date.month
    if as_of.day < hire_date.day:
        months -= 1
    if months < 0:
        years  -= 1
        months += 12
    return years, months


def calc_annual_leave_days(hire_date: date, as_of: date | None = None) -> int:
    """
    勞基法第 38 條特休天數：
    未滿 6 個月  → 0 天
    6 個月～1 年 → 3 天
    1～2 年      → 7 天
    2～3 年      → 10 天
    3～5 年      → 14 天
    5～10 年     → 15 天
    10 年以上    → 每年 +1 天，上限 30 天
    """
    if as_of is None:
        as_of = date.today()

    years, months = calc_seniority_months(hire_date, as_of)
    total_months  = years * 12 + months

    if total_months < 6:
        return 0
    if total_months < 12:
        return 3
    if years < 2:
        return 7
    if years < 3:
        return 10
    if years < 5:
        return 14
    if years < 10:
        return 15
    return min(15 + (years - 10), 30)


def get_all_quotas(
    hire_date_str: str,
    leave_types: list[LeaveTypeLike],
    as_of: date | None = None,
) -> list[dict]:
    """
    回傳所有假別的額度列表，依 leave_types 的 quota_type 決定計算方式：
      - seniority：依到職年資計算（目前只有「特休」用這個）
      - fixed：固定年度額度，直接用 quota_hours
      - unlimited：無上限（婚假、喪假、公假、其他）
    as_of 預設為今天，可指定特定日期（例如：年度第一天）計算當年度特休。
    """
    if as_of is None:
        as_of = date.today()

    hire = date.fromisoformat(hire_date_str)

    result = []
    for lt in leave_types:
        if lt.quota_type == "seniority":
            annual_days = calc_annual_leave_days(hire, as_of)
            result.append({
                "type":        lt.code,
                "total_days":  annual_days,
                "total_hours": annual_days * HOURS_PER_DAY,
                "note":        _seniority_label(hire, as_of),
            })
        elif lt.quota_type == "fixed":
            days = lt.quota_hours // HOURS_PER_DAY if lt.quota_hours is not None else None
            result.append({
                "type":        lt.code,
                "total_days":  days,
                "total_hours": lt.quota_hours,
                "note":        None,
            })
        else:  # unlimited
            result.append({
                "type":        lt.code,
                "total_days":  None,
                "total_hours": None,
                "note":        "無上限",
            })

    return result


def get_anniversary_year_start(hire_date: date, as_of: date) -> date:
    """回傳 as_of 所在的到職週年度起始日（含當天），處理 2/29 閏年邊界。"""
    year = as_of.year
    try:
        ann = hire_date.replace(year=year)
    except ValueError:
        ann = date(year, hire_date.month, 28)
    if ann > as_of:
        year -= 1
        try:
            ann = hire_date.replace(year=year)
        except ValueError:
            ann = date(year, hire_date.month, 28)
    return ann


def get_anniversary_year_end(hire_date: date, year_start: date) -> date:
    """回傳週年度最後一天（year_start 的隔年前一天）。"""
    next_year = year_start.year + 1
    try:
        next_ann = hire_date.replace(year=next_year)
    except ValueError:
        next_ann = date(next_year, hire_date.month, 28)
    return next_ann - timedelta(days=1)


def _seniority_label(hire_date: date, as_of: date) -> str:
    years, months = calc_seniority_months(hire_date, as_of)
    if years == 0:
        return f"年資 {months} 個月"
    if months == 0:
        return f"年資 {years} 年"
    return f"年資 {years} 年 {months} 個月"
