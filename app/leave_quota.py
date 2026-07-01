"""
台灣勞基法假別額度計算

特休（勞基法第 38 條）依年資計算，其餘假別為固定年度額度。
所有天數皆轉換為小時（1 天 = 8 小時）。
年度以「到職週年日」為基準重置。
"""

from datetime import date, timedelta

HOURS_PER_DAY = 8


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


# 固定年度額度（天）
# 病假：30 天（勞基法第 43 條，含住院與非住院合計上限）
# 事假：14 天（勞基法第 43 條）
# 婚假：8 天（勞工請假規則第 2 條）
# 喪假：最高 8 天（父母/配偶/子女，勞工請假規則第 3 條）
# 公假：0（無固定上限，依實際需要給）
# 其他：0（自訂，不設上限）
_FIXED_DAYS: dict[str, int | None] = {
    "病假": 30,
    "事假": 14,
    "婚假": 8,
    "喪假": 8,
    "公假": None,
    "其他": None,
}


def get_all_quotas(hire_date_str: str, as_of: date | None = None) -> list[dict]:
    """
    回傳所有假別的額度列表。
    as_of 預設為今天，可指定特定日期（例如：年度第一天）計算當年度特休。
    """
    if as_of is None:
        as_of = date.today()

    hire = date.fromisoformat(hire_date_str)
    annual_days = calc_annual_leave_days(hire, as_of)

    result = [
        {
            "type":        "特休",
            "total_days":  annual_days,
            "total_hours": annual_days * HOURS_PER_DAY,
            "note":        _seniority_label(hire, as_of),
        }
    ]

    for leave_type, days in _FIXED_DAYS.items():
        result.append({
            "type":        leave_type,
            "total_days":  days,
            "total_hours": days * HOURS_PER_DAY if days is not None else None,
            "note":        "無上限" if days is None else None,
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
