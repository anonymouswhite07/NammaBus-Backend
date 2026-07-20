import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websocket.manager import manager

router = APIRouter()

@router.websocket("/location/{route_id}")
async def websocket_location_endpoint(
    websocket: WebSocket,
    route_id: str
):
    """Realtime GPS coordination WebSocket. Buses broadcast their location; passengers listen."""
    await manager.connect_location(websocket, route_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # Expected payload: {"bus_id": "...", "latitude": 12.97, "longitude": 77.59, "speed": 40.0}
            latitude = payload.get("latitude")
            longitude = payload.get("longitude")
            
            if latitude is not None and longitude is not None:
                # Broadcast coordinate updates to route listeners
                await manager.broadcast_location(
                    route_id,
                    {
                        "bus_id": payload.get("bus_id"),
                        "latitude": latitude,
                        "longitude": longitude,
                        "speed": payload.get("speed", 0.0),
                        "bearing": payload.get("bearing", 0.0)
                    }
                )
    except WebSocketDisconnect:
        manager.disconnect_location(websocket, route_id)
