from datetime import timedelta, timezone, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core import security
from app.core.limiter import limiter
from app.repositories.all_repositories import user_repo, role_repo, token_repo
from app.schemas.all_schemas import (
    StandardResponse, Token, UserCreate, UserResponse, UserRegister, UserFirebaseCreate
)
from app.services.firebase_service import FirebaseService

router = APIRouter()

@router.post("/register", response_model=StandardResponse[UserResponse])
@limiter.limit("5/minute")
async def register(
    request: Request,
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """Registers a new Passenger user."""
    existing_user = await user_repo.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
        
    passenger_role = await role_repo.get_by_name(db, name="Passenger")
    if not passenger_role:
        # Create roles if they don't exist yet (first registration setup helper)
        passenger_role = await role_repo.create(
            db, obj_in={"name": "Passenger", "description": "Regular commuter Passenger user role"}
        )
        await role_repo.create(db, obj_in={"name": "Super Admin", "description": "Platform owner Admin"})
        await role_repo.create(db, obj_in={"name": "Transport Admin", "description": "Bus Fleet Operator Admin"})
        await role_repo.create(db, obj_in={"name": "Moderator", "description": "Transit content Moderator"})
        
    hashed_pwd = security.get_password_hash(user_in.password)
    user_obj = {
        "email": user_in.email,
        "full_name": user_in.full_name,
        "hashed_password": hashed_pwd,
        "role_id": passenger_role.id
    }
    
    new_user = await user_repo.create(db, obj_in=user_obj)
    return StandardResponse(
        success=True,
        message="User registered successfully.",
        data=UserResponse.model_validate(new_user)
    )

@router.post("/login", response_model=StandardResponse[Token])
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Logs in an email/password user and yields JWT tokens."""
    user = await user_repo.get_by_email(db, email=form_data.username)
    if not user or not user.hashed_password or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password."
        )
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account."
        )
        
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    # Cache the refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await token_repo.create(
        db,
        obj_in={
            "token": refresh_token,
            "user_id": user.id,
            "expires_at": expires_at
        }
    )
    
    return StandardResponse(
        success=True,
        message="Log in successful.",
        data=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/firebase-login", response_model=StandardResponse[Token])
async def firebase_login(
    firebase_in: UserFirebaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """Verifies Firebase Token, registers the profile if new, and yields local JWT tokens."""
    try:
        firebase_payload = FirebaseService.verify_token(firebase_in.firebase_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
        
    email = firebase_payload["email"]
    uid = firebase_payload["uid"]
    name = firebase_payload["name"]
    
    user = await user_repo.get_by_firebase_uid(db, firebase_uid=uid)
    if not user:
        # Check if email is already taken
        user = await user_repo.get_by_email(db, email=email)
        if user:
            # Map existing user to this Firebase ID
            user.firebase_uid = uid
            db.add(user)
            await db.flush()
        else:
            # Create a new user with Firebase identity
            passenger_role = await role_repo.get_by_name(db, name=firebase_in.role_name)
            if not passenger_role:
                passenger_role = await role_repo.create(db, obj_in={"name": firebase_in.role_name})
            
            user_obj = {
                "email": email,
                "full_name": name or firebase_in.full_name,
                "firebase_uid": uid,
                "role_id": passenger_role.id
            }
            user = await user_repo.create(db, obj_in=user_obj)
            
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await token_repo.create(
        db,
        obj_in={
            "token": refresh_token,
            "user_id": user.id,
            "expires_at": expires_at
        }
    )
    
    return StandardResponse(
        success=True,
        message="Firebase log in successful.",
        data=Token(access_token=access_token, refresh_token=refresh_token)
    )

@router.post("/refresh", response_model=StandardResponse[Token])
async def refresh(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refreshes an access token given a valid, non-expired refresh token."""
    db_token = await token_repo.get_by_token(db, token=refresh_token)
    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired refresh token."
        )
        
    access_token = security.create_access_token(subject=db_token.user_id)
    new_refresh_token = security.create_refresh_token(subject=db_token.user_id)
    
    # Revoke old refresh token
    db_token.revoked = True
    db.add(db_token)
    
    # Cache new refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await token_repo.create(
        db,
        obj_in={
            "token": new_refresh_token,
            "user_id": db_token.user_id,
            "expires_at": expires_at
        }
    )
    
    return StandardResponse(
        success=True,
        message="Token refreshed successfully.",
        data=Token(access_token=access_token, refresh_token=new_refresh_token)
    )
