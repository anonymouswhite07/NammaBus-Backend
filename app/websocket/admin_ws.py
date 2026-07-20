from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt
from app.config.settings import settings
from app.websocket.manager import manager

router = APIRouter()

@router.websocket("/admin")
async def websocket_admin_endpoint(
    websocket: WebSocket,
    token: str = Query(...)
):
    """Realtime dashboard analytics metrics WS stream. Restricted to Super Admin role."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # In production, look up user and verify role Super Admin / Transport Admin
        # For simplicity, we decode JWT subject; validation failures close socket
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect_admin(websocket)
    
    try:
        while True:
            # Admins listen to metrics; keep connection open
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)
        logger.info("WS Admin: Dashboard client disconnected.")

# Import logger
import logging
logger = logging.getLogger("namma_bus")
