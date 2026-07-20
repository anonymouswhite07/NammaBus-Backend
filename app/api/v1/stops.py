import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import stop_repo
from app.schemas.all_schemas import StandardResponse, StopResponse, StopCreate

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("", response_model=StandardResponse[List[StopResponse]])
async def list_stops(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lists or searches bus stops in the system."""
    if search:
        stops = await stop_repo.search_stops(db, query_str=search)
    else:
        stops = await stop_repo.get_multi(db, skip=skip, limit=limit)
    return StandardResponse(
        success=True,
        message="Stops retrieved successfully.",
        data=[StopResponse.model_validate(s) for s in stops]
    )

@router.get("/nearby", response_model=StandardResponse[List[StopResponse]])
async def get_nearby_stops(
    latitude: float,
    longitude: float,
    radius: float = 2.0, # in kilometers
    db: AsyncSession = Depends(get_db)
):
    """Retrieves bus stops located within a specified radius (in km) from GPS coordinates."""
    stops = await stop_repo.get_nearby_stops(db, lat=latitude, lon=longitude, radius_km=radius)
    return StandardResponse(
        success=True,
        message="Nearby stops retrieved successfully.",
        data=[StopResponse.model_validate(s) for s in stops]
    )

@router.post("", response_model=StandardResponse[StopResponse])
async def create_stop(
    stop_in: StopCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Creates a new bus stop with coordinates. Requires Admin role."""
    new_stop = await stop_repo.create(db, obj_in=stop_in.model_dump())
    return StandardResponse(
        success=True,
        message="Bus stop created successfully.",
        data=StopResponse.model_validate(new_stop)
    )
