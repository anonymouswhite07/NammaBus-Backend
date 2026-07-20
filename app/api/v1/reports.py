import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.limiter import limiter
from app.authentication.dependencies import get_current_active_user
from app.repositories.all_repositories import report_repo, route_repo, stop_repo, analytics_log_repo
from app.schemas.all_schemas import StandardResponse, PassengerReportResponse, PassengerReportCreate

router = APIRouter()

@router.post("", response_model=StandardResponse[PassengerReportResponse])
@limiter.limit("5/minute")
async def submit_passenger_report(
    request: Request,
    report_in: PassengerReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Submits a crowdsourced passenger transit report (e.g. bus location, crowds, delays, traffic, breakdown)."""
    route = await route_repo.get(db, id=report_in.route_id)
    if not route:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Route not found.")
        
    stop = await stop_repo.get(db, id=report_in.stop_id)
    if not stop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bus stop not found.")
        
    # Build database payload
    report_data = report_in.model_dump()
    report_data["user_id"] = current_user.id
    
    new_report = await report_repo.create(db, obj_in=report_data)
    
    # Audit/Log event to Analytics Log
    await analytics_log_repo.create(
        db,
        obj_in={
            "event_type": "REPORT_SUBMIT",
            "payload": {
                "user_id": str(current_user.id),
                "route_id": str(report_in.route_id),
                "report_type": report_in.report_type,
                "delay_minutes": report_in.delay_minutes,
                "crowd_level": report_in.crowd_level
            }
        }
    )
    
    return StandardResponse(
        success=True,
        message="Commuter report submitted successfully.",
        data=PassengerReportResponse.model_validate(new_report)
    )

@router.get("/active", response_model=StandardResponse[List[PassengerReportResponse]])
async def list_active_reports(
    minutes: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves active transit reports submitted within the last N minutes."""
    reports = await report_repo.get_active_reports(db, minutes=minutes)
    return StandardResponse(
        success=True,
        message="Active reports retrieved.",
        data=[PassengerReportResponse.model_validate(r) for r in reports]
    )
