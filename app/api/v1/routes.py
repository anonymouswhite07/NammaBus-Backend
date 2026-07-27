import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import route_repo, route_stop_repo, stop_repo
from app.schemas.all_schemas import (
    StandardResponse, RouteResponse, RouteCreate, RouteUpdate, RouteStopCreate, RouteStopResponse
)

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("", response_model=StandardResponse[List[RouteResponse]])
async def list_routes(
    search: Optional[str] = None,
    local_time: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lists or searches routes in the system."""
    if search:
        routes = await route_repo.search_routes(db, query_str=search, ref_time_str=local_time)
    else:
        routes = await route_repo.get_multi(db, skip=skip, limit=limit)
    return StandardResponse(
        success=True,
        message="Routes retrieved successfully.",
        data=[RouteResponse.model_validate(r) for r in routes]
    )

@router.get("/{id}", response_model=StandardResponse[RouteResponse])
async def get_route(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves details of a single route."""
    route = await route_repo.get(db, id=id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found."
        )
    return StandardResponse(
        success=True,
        message="Route details retrieved.",
        data=RouteResponse.model_validate(route)
    )

@router.post("", response_model=StandardResponse[RouteResponse])
async def create_route(
    route_in: RouteCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Creates a new transit route. Requires Admin role."""
    existing = await route_repo.get_by_route_number(db, route_number=route_in.route_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Route number already exists."
        )
    new_route = await route_repo.create(db, obj_in=route_in.model_dump())
    return StandardResponse(
        success=True,
        message="Route created successfully.",
        data=RouteResponse.model_validate(new_route)
    )

@router.put("/{id}", response_model=StandardResponse[RouteResponse])
async def update_route(
    id: uuid.UUID,
    route_in: RouteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Updates a route's details. Requires Admin role."""
    route = await route_repo.get(db, id=id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found."
        )
    updated_route = await route_repo.update(db, db_obj=route, obj_in=route_in)
    return StandardResponse(
        success=True,
        message="Route details updated.",
        data=RouteResponse.model_validate(updated_route)
    )

@router.delete("/{id}", response_model=StandardResponse[RouteResponse])
async def delete_route(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Soft deletes a route from the active system. Requires Admin role."""
    route = await route_repo.remove(db, id=id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found."
        )
    return StandardResponse(
        success=True,
        message="Route deactivated and soft-deleted.",
        data=RouteResponse.model_validate(route)
    )

@router.post("/{id}/stops", response_model=StandardResponse[List[RouteStopResponse]])
async def assign_stops(
    id: uuid.UUID,
    stops_in: List[RouteStopCreate],
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Assigns an ordered list of stops to a route. Requires Admin role."""
    route = await route_repo.get(db, id=id)
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found."
        )
        
    # Delete existing stops for this route
    existing_stops = await route_stop_repo.get_by_route(db, route_id=id)
    for es in existing_stops:
        await route_stop_repo.hard_remove(db, id=es.id)
        
    created_stops = []
    for si in stops_in:
        stop = await stop_repo.get(db, id=si.stop_id)
        if not stop:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stop with ID {si.stop_id} not found."
            )
        rs = await route_stop_repo.create(
            db,
            obj_in={
                "route_id": id,
                "stop_id": si.stop_id,
                "sequence_order": si.sequence_order
            }
        )
        created_stops.append(rs)
        
    return StandardResponse(
        success=True,
        message="Route stops assigned successfully.",
        data=[RouteStopResponse.model_validate(cs) for cs in created_stops]
    )
