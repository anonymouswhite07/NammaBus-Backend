from fastapi import APIRouter
from app.api.v1 import (
    auth, buses, routes, stops, timetable, reports, favorites, notifications, ads, admin, analytics
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(buses.router, prefix="/buses", tags=["Buses & Operators"])
api_router.include_router(routes.router, prefix="/routes", tags=["Routes"])
api_router.include_router(stops.router, prefix="/stops", tags=["Stops"])
api_router.include_router(timetable.router, prefix="/timetable", tags=["Timetable"])
api_router.include_router(reports.router, prefix="/report", tags=["Passenger Reports"])
api_router.include_router(favorites.router, prefix="/favourite", tags=["Starred Favorites"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(ads.router, prefix="/ads", tags=["Advertisements"])
api_router.include_router(admin.router, prefix="/admin", tags=["Super Admin"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["System Analytics"])
