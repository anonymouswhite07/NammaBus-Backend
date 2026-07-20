from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import RoleChecker
from app.repositories.all_repositories import report_repo, route_repo, chat_msg_repo, analytics_log_repo

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("/peak-hours")
async def get_peak_travel_hours(
    db: AsyncSession = Depends(get_db)
):
    """Calculates peak travel hours based on passenger report submission timestamps."""
    query = (
        select(
            func.extract("hour", report_repo.model.created_at).label("hour"),
            func.count(report_repo.model.id).label("report_count")
        )
        .group_by("hour")
        .order_by(func.count(report_repo.model.id).desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    return {
        "success": True,
        "message": "Peak travel hours analytics calculated.",
        "data": [{"hour": int(row[0]), "count": int(row[1])} for row in rows]
    }

@router.get("/crowded-routes")
async def get_most_crowded_routes(
    db: AsyncSession = Depends(get_db)
):
    """Identifies the most crowded routes based on passenger report values (CROWDED, HEAVY_TRAFFIC)."""
    query = (
        select(
            route_repo.model.route_number,
            func.count(report_repo.model.id).label("crowded_report_count")
        )
        .join(report_repo.model, report_repo.model.route_id == route_repo.model.id)
        .filter(
            and_(
                report_repo.model.report_type.in_(["CROWDED", "HEAVY_TRAFFIC"]),
                report_repo.model.deleted_at == None
            )
        )
        .group_by(route_repo.model.route_number)
        .order_by(func.count(report_repo.model.id).desc())
        .limit(10)
    )
    result = await db.execute(query)
    rows = result.all()
    
    return {
        "success": True,
        "message": "Most crowded routes loaded.",
        "data": [{"route_number": row[0], "count": int(row[1])} for row in rows]
    }

@router.get("/average-delays")
async def get_average_delays_per_route(
    db: AsyncSession = Depends(get_db)
):
    """Calculates the average delay in minutes per transit route."""
    query = (
        select(
            route_repo.model.route_number,
            func.avg(report_repo.model.delay_minutes).label("avg_delay")
        )
        .join(report_repo.model, report_repo.model.route_id == route_repo.model.id)
        .filter(report_repo.model.deleted_at == None)
        .group_by(route_repo.model.route_number)
        .order_by(func.avg(report_repo.model.delay_minutes).desc())
    )
    result = await db.execute(query)
    rows = result.all()
    
    return {
        "success": True,
        "message": "Average route delays calculated.",
        "data": [{"route_number": row[0], "average_delay_minutes": float(row[1])} for row in rows]
    }
