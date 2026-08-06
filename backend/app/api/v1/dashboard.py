"""預約儀表板統計。"""
from collections import defaultdict
from datetime import datetime, date, time, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from ...db.session import get_db
from ...models import Reservation, Resource, User
from ...schemas import DashboardStats
from ..deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["reservation"])


@router.get("/reservation", response_model=DashboardStats)
def reservation_dashboard(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tz = timezone.utc
    start = datetime.combine(from_date, time.min, tzinfo=tz)
    end = datetime.combine(to_date, time.max, tzinfo=tz)

    # 1) 資源數量（room only for slice 1）
    resource_count = db.execute(
        select(func.count(Resource.id)).where(
            Resource.organization_id == user.organization_id,
            Resource.type == "room",
        )
    ).scalar_one()

    # 2) 預約清單
    resv = db.execute(
        select(Reservation).where(
            Reservation.organization_id == user.organization_id,
            Reservation.start_at <= end,
            Reservation.end_at >= start,
            Reservation.status.in_(["approved", "checked_in"]),
        )
    ).scalars().all()

    total_seconds = sum((r.end_at - r.start_at).total_seconds() for r in resv)
    total_hours = round(total_seconds / 3600, 1)

    # 3) 可用小時：資源數量 * 天數 * 24 （粗略）
    days = (to_date - from_date).days + 1
    total_available_hours = resource_count * days * 24
    utilization = (total_hours / total_available_hours) if total_available_hours > 0 else 0

    # 4) 每日小時
    daily = defaultdict(float)
    cur = from_date
    while cur <= to_date:
        daily[cur.isoformat()] = 0.0
        cur += timedelta(days=1)
    for r in resv:
        day = r.start_at.date().isoformat()
        daily[day] += (r.end_at - r.start_at).total_seconds() / 3600

    # 5) 依類型
    by_type = {"normal": 0, "recurring": 0, "walk_in": 0}
    for r in resv:
        by_type[r.type] = by_type.get(r.type, 0) + 1

    # 6) 依時長
    buckets = {"<=30": 0, "30-60": 0, "60-90": 0, "90-120": 0, "120-180": 0, "180-240": 0, "240-360": 0, ">360": 0}
    for r in resv:
        m = (r.end_at - r.start_at).total_seconds() / 60
        if m <= 30: buckets["<=30"] += 1
        elif m <= 60: buckets["30-60"] += 1
        elif m <= 90: buckets["60-90"] += 1
        elif m <= 120: buckets["90-120"] += 1
        elif m <= 180: buckets["120-180"] += 1
        elif m <= 240: buckets["180-240"] += 1
        elif m <= 360: buckets["240-360"] += 1
        else: buckets[">360"] += 1

    return DashboardStats(
        resource_count=resource_count,
        reservation_count=len(resv),
        total_hours=total_hours,
        utilization_rate=round(utilization, 4),
        total_available_hours=total_available_hours,
        daily_hours=[{"date": k, "hours": round(v, 2)} for k, v in sorted(daily.items())],
        by_type=by_type,
        by_duration=buckets,
    )
