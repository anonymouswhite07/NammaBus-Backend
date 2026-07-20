import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user
from app.repositories.all_repositories import route_repo, user_repo
from app.schemas.all_schemas import StandardResponse, RouteResponse

router = APIRouter()

@router.post("/{route_id}", response_model=StandardResponse[bool])
async def toggle_favourite_route(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Toggles (stars / unstars) a commute route in the user's favorites list."""
    route = await route_repo.get(db, id=route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found.")
        
    # Eager load favorites
    query = select(user_repo.model).filter(user_repo.model.id == current_user.id).options(selectinload(user_repo.model.favorites))
    res = await db.execute(query)
    user_loaded = res.scalars().first()
    
    is_faved = False
    if route in user_loaded.favorites:
        user_loaded.favorites.remove(route)
    else:
        user_loaded.favorites.append(route)
        is_faved = True
        
    db.add(user_loaded)
    await db.flush()
    
    message = "Route added to favorites." if is_faved else "Route removed from favorites."
    return StandardResponse(
        success=True,
        message=message,
        data=is_faved
    )

@router.get("", response_model=StandardResponse[List[RouteResponse]])
async def get_favourite_routes(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Retrieves all starred transit routes of the logged-in user."""
    query = select(user_repo.model).filter(user_repo.model.id == current_user.id).options(selectinload(user_repo.model.favorites))
    res = await db.execute(query)
    user_loaded = res.scalars().first()
    
    active_favorites = [f for f in user_loaded.favorites if f.deleted_at is None]
    return StandardResponse(
        success=True,
        message="Starred routes list loaded.",
        data=[RouteResponse.model_validate(f) for f in active_favorites]
    )
