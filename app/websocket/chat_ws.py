import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from jose import jwt
from app.config.settings import settings
from app.database.session import get_raw_db
from app.repositories.all_repositories import user_repo, chat_room_repo, chat_msg_repo
from app.websocket.manager import manager

router = APIRouter()

async def authenticate_ws(websocket: WebSocket, token: str) -> dict:
    """Verifies access token query parameter and extracts user identity."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return {"user_id": user_id}
    except Exception:
        return None

@router.websocket("/chat/{route_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    route_id: str,
    token: str = Query(...)
):
    # Authenticate token
    auth_payload = await authenticate_ws(websocket, token)
    if not auth_payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = auth_payload["user_id"]
    db = await get_raw_db()
    
    try:
        # Load user name and room
        user = await user_repo.get(db, id=user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        chat_room = await chat_room_repo.get_by_route(db, route_id=route_id)
        if not chat_room:
            # Create room dynamically if missing
            chat_room = await chat_room_repo.create(db, obj_in={"route_id": route_id})
            await db.commit()

        # Connect to manager
        await manager.connect_chat(websocket, route_id)
        
        # Broadcast join notification
        await manager.broadcast_to_chat(
            route_id,
            {
                "event": "JOIN",
                "user_name": user.full_name,
                "online_count": manager.get_online_users(route_id)
            }
        )

        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            event_type = payload.get("event", "MESSAGE")
            
            if event_type == "TYPING":
                # Broadcast typing indicator to room
                await manager.broadcast_to_chat(
                    route_id,
                    {
                        "event": "TYPING",
                        "user_name": user.full_name,
                        "is_typing": payload.get("is_typing", True)
                    }
                )
            elif event_type == "MESSAGE":
                msg_text = payload.get("message", "").strip()
                if msg_text:
                    # Save chat message to database
                    await chat_msg_repo.create(
                        db,
                        obj_in={
                            "chat_room_id": chat_room.id,
                            "user_id": user.id,
                            "message": msg_text,
                            "message_type": payload.get("message_type", "TEXT")
                        }
                    )
                    await db.commit()
                    
                    # Broadcast message to room
                    await manager.broadcast_to_chat(
                        route_id,
                        {
                            "event": "MESSAGE",
                            "user_name": user.full_name,
                            "message": msg_text,
                            "message_type": payload.get("message_type", "TEXT"),
                            "created_at": str(datetime.now())
                        }
                    )

    except WebSocketDisconnect:
        manager.disconnect_chat(websocket, route_id)
        # Broadcast leave notification
        await manager.broadcast_to_chat(
            route_id,
            {
                "event": "LEAVE",
                "user_name": user.full_name,
                "online_count": manager.get_online_users(route_id)
            }
        )
    finally:
        await db.close()

# Helper for datetime
from datetime import datetime
