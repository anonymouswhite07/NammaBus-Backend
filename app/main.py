import time
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.config.settings import settings
from app.api.router import api_router
from app.core import logger # Registers structured logs
from app.core.limiter import limiter
from app.websocket import chat_ws, location_ws, notification_ws, admin_ws

from contextlib import asynccontextmanager
from app.database.base import Base
from app.database.session import engine, AsyncSessionLocal
from app.repositories.all_repositories import role_repo, user_repo
from app.core import security

logger = logging.getLogger("namma_bus")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database schema
    logger.info("Initializing SQLite database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Seed default roles and admin account
    async with AsyncSessionLocal() as db:
        passenger_role = await role_repo.get_by_name(db, name="Passenger")
        if not passenger_role:
            logger.info("Seeding roles and default admin account...")
            passenger_role = await role_repo.create(db, obj_in={"name": "Passenger", "description": "Commuter Passenger"})
            super_admin_role = await role_repo.create(db, obj_in={"name": "Super Admin", "description": "Platform Admin"})
            await role_repo.create(db, obj_in={"name": "Transport Admin", "description": "Fleet Operator"})
            await role_repo.create(db, obj_in={"name": "Moderator", "description": "Chat Moderator"})
            
            admin_user = await user_repo.get_by_email(db, email="admin@nammabus.com")
            if not admin_user:
                await user_repo.create(db, obj_in={
                    "email": "admin@nammabus.com",
                    "full_name": "SYSTEM ADMINISTRATOR",
                    "hashed_password": security.get_password_hash("admin123"),
                    "role_id": super_admin_role.id,
                    "is_active": True
                })
            await db.commit()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Register slowapi rate limiter state and error handlers
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Policy
if settings.BACKEND_CORS_ORIGINS:
    origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS]
    use_regex = False
    if len(origins) == 1 and origins[0] == "*":
        use_regex = True
        origins = []

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https?://(localhost:\d+|.*\.vercel\.app)" if use_regex else None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# REST API Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Realtime WebSocket Endpoints
app.include_router(chat_ws.router, prefix="/ws")
app.include_router(location_ws.router, prefix="/ws")
app.include_router(notification_ws.router, prefix="/ws")
app.include_router(admin_ws.router, prefix="/ws")

# Global Standard Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "An unexpected server error occurred.",
            "data": {"detail": str(exc)}
        }
    )

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "message": str(exc),
            "data": None
        }
    )

# Middleware: Request duration diagnostics logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"API Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - Duration: {duration:.4f}s"
    )
    return response

@app.get("/", tags=["Root"])
async def root_redirect():
    """Index root checkpoint confirming API status."""
    return {
        "success": True,
        "message": f"Welcome to the {settings.PROJECT_NAME} gateway! Access Swagger documentation at /docs",
        "data": {
            "environment": "production-ready",
            "version": "v1.0.0"
        }
    }
