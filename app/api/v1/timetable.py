import io
import uuid
import pandas as pd
from datetime import time, datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import timetable_repo, route_repo, stop_repo
from app.schemas.all_schemas import StandardResponse, TimetableResponse, TimetableCreate

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("/{route_id}", response_model=StandardResponse[List[TimetableResponse]])
async def get_route_timetable(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves all scheduled stop timings for a specific route."""
    query = select(timetable_repo.model).filter(timetable_repo.model.route_id == route_id).order_by(timetable_repo.model.arrival_time)
    result = await db.execute(query)
    timetables = result.scalars().all()
    return StandardResponse(
        success=True,
        message="Route timetable retrieved.",
        data=[TimetableResponse.model_validate(t) for t in timetables]
    )

@router.post("", response_model=StandardResponse[TimetableResponse])
async def create_timetable_entry(
    timetable_in: TimetableCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Creates a single scheduled timetable entry. Requires Admin role."""
    route = await route_repo.get(db, id=timetable_in.route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route not found.")
        
    stop = await stop_repo.get(db, id=timetable_in.stop_id)
    if not stop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bus stop not found.")
        
    new_entry = await timetable_repo.create(db, obj_in=timetable_in.model_dump())
    return StandardResponse(
        success=True,
        message="Timetable entry created.",
        data=TimetableResponse.model_validate(new_entry)
    )

@router.put("/{id}", response_model=StandardResponse[TimetableResponse])
async def update_timetable_entry(
    id: uuid.UUID,
    timetable_in: dict,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Updates a scheduled timetable entry. Requires Admin role."""
    entry = await timetable_repo.get(db, id=id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found.")
        
    updated_entry = await timetable_repo.update(db, db_obj=entry, obj_in=timetable_in)
    return StandardResponse(
        success=True,
        message="Timetable entry updated successfully.",
        data=TimetableResponse.model_validate(updated_entry)
    )

@router.delete("/{id}", response_model=StandardResponse[dict])
async def delete_timetable_entry(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Deletes a single scheduled timetable entry. Requires Admin role."""
    entry = await timetable_repo.get(db, id=id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable entry not found.")
        
    await timetable_repo.remove(db, id=id)
    return StandardResponse(
        success=True,
        message="Timetable entry deleted successfully.",
        data={"id": str(id)}
    )

@router.post("/import-csv", response_model=StandardResponse[dict])
async def import_timetable_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Imports a bulk set of scheduled timings from a CSV file. Requires Admin role."""
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV formatting: {e}"
        )
        
    required_cols = {"route_number", "stop_name", "arrival_time", "departure_time", "day_of_week"}
    if not required_cols.issubset(df.columns):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CSV is missing one or more required columns: {required_cols}"
        )
        
    imported_count = 0
    errors = []
    
    for idx, row in df.iterrows():
        try:
            route = await route_repo.get_by_route_number(db, route_number=str(row["route_number"]))
            if not route:
                errors.append(f"Row {idx}: Route '{row['route_number']}' not found.")
                continue
                
            stops = await stop_repo.search_stops(db, query_str=str(row["stop_name"]))
            if not stops:
                errors.append(f"Row {idx}: Stop '{row['stop_name']}' not found.")
                continue
            stop = stops[0]
            
            # Parse times
            arr_t = datetime.strptime(str(row["arrival_time"]).strip(), "%H:%M").time()
            dep_t = datetime.strptime(str(row["departure_time"]).strip(), "%H:%M").time()
            
            await timetable_repo.create(
                db,
                obj_in={
                    "route_id": route.id,
                    "stop_id": stop.id,
                    "arrival_time": arr_t,
                    "departure_time": dep_t,
                    "day_of_week": str(row["day_of_week"]).strip()
                }
            )
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {idx}: Failed to import: {e}")
            
    return StandardResponse(
        success=True,
        message=f"Timetable import completed. Imported: {imported_count}. Failed: {len(errors)}.",
        data={"imported_count": imported_count, "errors": errors}
    )

@router.get("/export-csv/{route_id}")
async def export_timetable_csv(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    """Exports all timetable entries of a route to a downloadable CSV file."""
    route = await route_repo.get(db, id=route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route not found.")
        
    query = select(timetable_repo.model).filter(timetable_repo.model.route_id == route_id)
    result = await db.execute(query)
    timetables = result.scalars().all()
    
    data = []
    for t in timetables:
        stop = await stop_repo.get(db, id=t.stop_id)
        data.append({
            "route_number": route.route_number,
            "stop_name": stop.name if stop else "Unknown",
            "arrival_time": t.arrival_time.strftime("%H:%M") if hasattr(t.arrival_time, 'strftime') else str(t.arrival_time),
            "departure_time": t.departure_time.strftime("%H:%M") if hasattr(t.departure_time, 'strftime') else str(t.departure_time),
            "day_of_week": t.day_of_week
        })
        
    df = pd.DataFrame(data)
    stream = io.StringIO()
    df.to_csv(stream, index=False)
    
    response = StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv"
    )
    response.headers["Content-Disposition"] = f"attachment; filename=timetable_route_{route.route_number}.csv"
    return response
