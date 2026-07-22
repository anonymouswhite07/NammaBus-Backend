import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import RoleChecker
from app.repositories.all_repositories import user_repo, route_repo, bus_repo, report_repo, ad_repo
from app.schemas.all_schemas import StandardResponse, UserResponse

router = APIRouter()

# Super Admin authorization guard
super_admin_checker = RoleChecker(["Super Admin"])

@router.get("/dashboard", response_model=StandardResponse[dict])
async def get_admin_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(super_admin_checker)
):
    """Retrieves high-level dashboard summaries of Namma Bus. Requires Super Admin role."""
    # Count totals
    total_users_query = select(func.count(user_repo.model.id)).filter(user_repo.model.deleted_at == None)
    total_routes_query = select(func.count(route_repo.model.id)).filter(route_repo.model.deleted_at == None)
    total_buses_query = select(func.count(bus_repo.model.id)).filter(bus_repo.model.deleted_at == None)
    
    # Active reports (last 30 mins)
    active_reports_count = len(await report_repo.get_active_reports(db, minutes=30))
    
    # Ad performance logs
    ad_stats_query = select(
        func.sum(ad_repo.model.impressions),
        func.sum(ad_repo.model.clicks),
        func.sum(ad_repo.model.revenue)
    ).filter(ad_repo.model.deleted_at == None)
    
    total_users = (await db.execute(total_users_query)).scalar() or 0
    total_routes = (await db.execute(total_routes_query)).scalar() or 0
    total_buses = (await db.execute(total_buses_query)).scalar() or 0
    
    ad_res = (await db.execute(ad_stats_query)).first()
    impressions = ad_res[0] or 0 if ad_res else 0
    clicks = ad_res[1] or 0 if ad_res else 0
    revenue = ad_res[2] or 0.0 if ad_res else 0.0
    
    return StandardResponse(
        success=True,
        message="Dashboard summary loaded.",
        data={
            "metrics": {
                "total_users": total_users,
                "total_routes": total_routes,
                "total_buses": total_buses,
                "active_commuter_reports": active_reports_count
            },
            "sponsorship_analytics": {
                "total_ad_impressions": impressions,
                "total_ad_clicks": clicks,
                "estimated_revenue_usd": round(revenue, 2)
            }
        }
    )

@router.get("/users", response_model=StandardResponse[List[UserResponse]])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(super_admin_checker)
):
    """Lists all user accounts (including transit admins/moderators). Requires Super Admin role."""
    query = (
        select(user_repo.model)
        .filter(user_repo.model.deleted_at == None)
        .options(selectinload(user_repo.model.role))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    users = result.scalars().all()
    return StandardResponse(
        success=True,
        message="Users list loaded.",
        data=[UserResponse.model_validate(u) for u in users]
    )

@router.put("/users/{id}/deactivate", response_model=StandardResponse[UserResponse])
async def toggle_user_activation(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(super_admin_checker)
):
    """Toggles the active status of a user account. Requires Super Admin role."""
    user = await user_repo.get(db, id=id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        
    user.is_active = not user.is_active
    db.add(user)
    await db.flush()
    
    # Eager reload relation for response schema validation
    query = select(user_repo.model).filter(user_repo.model.id == id).options(selectinload(user_repo.model.role))
    res = await db.execute(query)
    user_loaded = res.scalars().first()
    
    message = "User activated successfully." if user_loaded.is_active else "User deactivated."
    return StandardResponse(
        success=True,
        message=message,
        data=UserResponse.model_validate(user_loaded)
    )
