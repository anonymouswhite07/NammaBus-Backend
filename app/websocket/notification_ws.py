from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt
from app.config.settings import settings
from app.websocket.manager import manager

router = APIRouter()

@router.websocket("/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """Realtime personal notifications push channel. Connects using user JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_notification(websocket, user_id)
    
    try:
        while True:
            # Notifications are push-only from backend; keep socket alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_notification(websocket, user_id)
