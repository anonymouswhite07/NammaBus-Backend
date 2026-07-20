import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import bus_repo, operator_repo
from app.schemas.all_schemas import (
    StandardResponse, BusResponse, BusCreate, BusUpdate, BusOperatorResponse, BusOperatorCreate
)

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])
super_admin_checker = RoleChecker(["Super Admin"])

@router.get("", response_model=StandardResponse[List[BusResponse]])
async def list_buses(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Lists or searches buses in the system."""
    if search:
        buses = await bus_repo.search_buses(db, query_str=search)
    else:
        buses = await bus_repo.get_multi(db, skip=skip, limit=limit)
    return StandardResponse(
        success=True,
        message="Buses retrieved successfully.",
        data=[BusResponse.model_validate(b) for b in buses]
    )

@router.get("/{id}", response_model=StandardResponse[BusResponse])
async def get_bus(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves details of a single bus."""
    bus = await bus_repo.get(db, id=id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found."
        )
    return StandardResponse(
        success=True,
        message="Bus details retrieved.",
        data=BusResponse.model_validate(bus)
    )

@router.post("", response_model=StandardResponse[BusResponse])
async def create_bus(
    bus_in: BusCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Creates a new bus. Requires Admin role."""
    operator = await operator_repo.get(db, id=bus_in.operator_id)
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bus Operator not found."
        )
    new_bus = await bus_repo.create(db, obj_in=bus_in.model_dump())
    return StandardResponse(
        success=True,
        message="Bus created successfully.",
        data=BusResponse.model_validate(new_bus)
    )

@router.put("/{id}", response_model=StandardResponse[BusResponse])
async def update_bus(
    id: uuid.UUID,
    bus_in: BusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Updates a bus's specifications. Requires Admin role."""
    bus = await bus_repo.get(db, id=id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found."
        )
    updated_bus = await bus_repo.update(db, db_obj=bus, obj_in=bus_in)
    return StandardResponse(
        success=True,
        message="Bus specifications updated.",
        data=BusResponse.model_validate(updated_bus)
    )

@router.delete("/{id}", response_model=StandardResponse[BusResponse])
async def delete_bus(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Soft deletes a bus from the active system. Requires Admin role."""
    bus = await bus_repo.remove(db, id=id)
    if not bus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bus not found."
        )
    return StandardResponse(
        success=True,
        message="Bus deactivated and soft-deleted.",
        data=BusResponse.model_validate(bus)
    )

# Operator Endpoints
@router.post("/operators", response_model=StandardResponse[BusOperatorResponse])
async def create_operator(
    operator_in: BusOperatorCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(super_admin_checker)
):
    """Registers a new transit operator company. Requires Super Admin role."""
    new_operator = await operator_repo.create(db, obj_in=operator_in.model_dump())
    return StandardResponse(
        success=True,
        message="Transit operator registered.",
        data=BusOperatorResponse.model_validate(new_operator)
    )
