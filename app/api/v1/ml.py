import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.ml.services import MLPredictorService
from app.schemas.all_schemas import StandardResponse

router = APIRouter()

@router.get("/predict-eta", response_model=StandardResponse[dict])
async def get_predicted_eta(
    route_id: uuid.UUID,
    stop_id: uuid.UUID,
    traffic_level: Optional[str] = "NORMAL",
    hour: Optional[int] = 12,
    db: AsyncSession = Depends(get_db)
):
    """Predicts estimated arrival delay minutes using historical timelines and traffic reports."""
    prediction = await MLPredictorService.predict_eta(
        db,
        route_id=str(route_id),
        stop_id=str(stop_id),
        traffic_level=traffic_level,
        hour_of_day=hour
    )
    return StandardResponse(
        success=True,
        message="Estimated delay predicted.",
        data=prediction
    )

@router.get("/predict-crowd", response_model=StandardResponse[dict])
async def get_predicted_crowd(
    route_id: uuid.UUID,
    stop_id: uuid.UUID,
    day_of_week: Optional[str] = "WEEKDAY",
    hour: Optional[int] = 8,
    db: AsyncSession = Depends(get_db)
):
    """Predicts crowd level (LOW, MEDIUM, HIGH) and seating probability."""
    prediction = await MLPredictorService.predict_crowd(
        db,
        route_id=str(route_id),
        stop_id=str(stop_id),
        day_of_week=day_of_week,
        hour_of_day=hour
    )
    return StandardResponse(
        success=True,
        message="Crowd level occupancy predicted.",
        data=prediction
    )
