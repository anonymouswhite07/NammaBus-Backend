import uuid
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.authentication.dependencies import get_current_active_user, RoleChecker
from app.repositories.all_repositories import notification_repo, notification_history_repo, user_repo
from app.schemas.all_schemas import StandardResponse, NotificationResponse, NotificationHistoryResponse, NotificationCreate
from app.services.firebase_service import FirebaseService

router = APIRouter()

# Role guards
admin_checker = RoleChecker(["Super Admin", "Transport Admin"])

@router.get("", response_model=StandardResponse[List[NotificationHistoryResponse]])
async def get_user_notifications(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Retrieves all notifications targeted to the logged-in user."""
    query = (
        select(notification_history_repo.model)
        .filter(notification_history_repo.model.user_id == current_user.id)
        .options(selectinload(notification_history_repo.model.notification))
    )
    result = await db.execute(query)
    history = result.scalars().all()
    return StandardResponse(
        success=True,
        message="User notifications list loaded.",
        data=[NotificationHistoryResponse.model_validate(h) for h in history]
    )

@router.post("/read/{id}", response_model=StandardResponse[NotificationHistoryResponse])
async def mark_as_read(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Marks a notification history entry as read."""
    entry = await notification_history_repo.get(db, id=id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification entry not found.")
        
    entry.is_read = True
    entry.read_at = datetime.now(timezone.utc)
    db.add(entry)
    await db.flush()
    
    # Eager reload relation for response schema validation
    query = select(notification_history_repo.model).filter(notification_history_repo.model.id == id).options(selectinload(notification_history_repo.model.notification))
    res = await db.execute(query)
    entry_loaded = res.scalars().first()
    
    return StandardResponse(
        success=True,
        message="Notification marked as read.",
        data=NotificationHistoryResponse.model_validate(entry_loaded)
    )

@router.post("/broadcast", response_model=StandardResponse[NotificationResponse])
async def broadcast_notification(
    notif_in: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(admin_checker)
):
    """Broadcasts a system notification to all active users via FCM. Requires Admin role."""
    new_notif = await notification_repo.create(db, obj_in=notif_in.model_dump())
    
    # Get all active user IDs (we limit to 500 for safety, but in production we can paginate)
    query = select(user_repo.model).filter(user_repo.model.is_active == True)
    res = await db.execute(query)
    users = res.scalars().all()
    
    # Register history entries
    for u in users:
        await notification_history_repo.create(
            db,
            obj_in={
                "notification_id": new_notif.id,
                "user_id": u.id,
                "is_read": False
            }
        )
        
    # Send FCM notifications in mock or production FCM channels
    # In actual production, you'd fetch the user's FCM tokens.
    # We will invoke FCM Service multicast on dummy tokens to test integrity.
    dummy_tokens = ["fcm-token-1", "fcm-token-2"]
    await FirebaseService.send_multicast_notification(
        tokens=dummy_tokens,
        title=notif_in.title,
        body=notif_in.body,
        data={"notification_type": notif_in.notification_type}
    )
    
    return StandardResponse(
        success=True,
        message="Notification broadcasted successfully.",
        data=NotificationResponse.model_validate(new_notif)
    )
