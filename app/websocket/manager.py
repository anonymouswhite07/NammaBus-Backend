import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("namma_bus")

class ConnectionManager:
    def __init__(self):
        # Maps route_id -> List of active WebSockets
        self.chat_rooms: Dict[str, Set[WebSocket]] = {}
        # Maps route_id -> List of active location listeners
        self.location_rooms: Dict[str, Set[WebSocket]] = {}
        # Maps user_id (str) -> Active WebSocket for notification channel
        self.notification_channels: Dict[str, Set[WebSocket]] = {}
        # List of active admin connections
        self.admin_connections: Set[WebSocket] = set()

    # Chat Room Handlers
    async def connect_chat(self, websocket: WebSocket, route_id: str):
        await websocket.accept()
        if route_id not in self.chat_rooms:
            self.chat_rooms[route_id] = set()
        self.chat_rooms[route_id].add(websocket)
        logger.info(f"WS Chat: Client connected to room {route_id}. Total: {len(self.chat_rooms[route_id])}")

    def disconnect_chat(self, websocket: WebSocket, route_id: str):
        if route_id in self.chat_rooms:
            self.chat_rooms[route_id].discard(websocket)
            if not self.chat_rooms[route_id]:
                del self.chat_rooms[route_id]
            logger.info(f"WS Chat: Client disconnected from room {route_id}.")

    async def broadcast_to_chat(self, route_id: str, message: dict):
        if route_id in self.chat_rooms:
            dead_sockets = []
            for ws in self.chat_rooms[route_id]:
                try:
                    await ws.send_text(json.dumps(message))
                except Exception:
                    dead_sockets.append(ws)
            # Cleanup broken sockets
            for ds in dead_sockets:
                self.disconnect_chat(ds, route_id)

    def get_online_users(self, route_id: str) -> int:
        return len(self.chat_rooms.get(route_id, []))

    # Location Handlers
    async def connect_location(self, websocket: WebSocket, route_id: str):
        await websocket.accept()
        if route_id not in self.location_rooms:
            self.location_rooms[route_id] = set()
        self.location_rooms[route_id].add(websocket)
        logger.info(f"WS Location: Listener joined route {route_id}.")

    def disconnect_location(self, websocket: WebSocket, route_id: str):
        if route_id in self.location_rooms:
            self.location_rooms[route_id].discard(websocket)
            if not self.location_rooms[route_id]:
                del self.location_rooms[route_id]

    async def broadcast_location(self, route_id: str, location_payload: dict):
        if route_id in self.location_rooms:
            dead_sockets = []
            for ws in self.location_rooms[route_id]:
                try:
                    await ws.send_text(json.dumps(location_payload))
                except Exception:
                    dead_sockets.append(ws)
            for ds in dead_sockets:
                self.disconnect_location(ds, route_id)

    # Notification Handlers
    async def connect_notification(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.notification_channels:
            self.notification_channels[user_id] = set()
        self.notification_channels[user_id].add(websocket)
        logger.info(f"WS Notifications: User {user_id} channel opened.")

    def disconnect_notification(self, websocket: WebSocket, user_id: str):
        if user_id in self.notification_channels:
            self.notification_channels[user_id].discard(websocket)
            if not self.notification_channels[user_id]:
                del self.notification_channels[user_id]

    async def send_personal_notification(self, user_id: str, notification: dict):
        if user_id in self.notification_channels:
            dead_sockets = []
            for ws in self.notification_channels[user_id]:
                try:
                    await ws.send_text(json.dumps(notification))
                except Exception:
                    dead_sockets.append(ws)
            for ds in dead_sockets:
                self.disconnect_notification(ds, user_id)

    # Admin Handlers
    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)
        logger.info("WS Admin: Dashboard client connected.")

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)

    async def broadcast_admin_metrics(self, metrics: dict):
        dead_sockets = []
        for ws in self.admin_connections:
            try:
                await ws.send_text(json.dumps(metrics))
            except Exception:
                dead_sockets.append(ws)
        for ds in dead_sockets:
            self.disconnect_admin(ds)

manager = ConnectionManager()
