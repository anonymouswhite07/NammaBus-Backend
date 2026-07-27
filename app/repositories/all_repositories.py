import uuid
from typing import List, Optional
from datetime import datetime, timezone, time
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.base_repository import BaseRepository
from app.models.all_models import (
    Role, User, RefreshToken, BusOperator, Bus, Route, Stop, RouteStop,
    Timetable, PassengerReport, ChatRoom, ChatMessage, Advertisement,
    Notification, NotificationHistory, MLPrediction, AnalyticsLog, AuditLog,
    ExtractedTimetable
)

class RoleRepository(BaseRepository[Role]):
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Role]:
        query = select(self.model).filter(self.model.name == name, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

class UserRepository(BaseRepository[User]):
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        query = select(self.model).filter(self.model.email == email, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_by_firebase_uid(self, db: AsyncSession, firebase_uid: str) -> Optional[User]:
        query = select(self.model).filter(self.model.firebase_uid == firebase_uid, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

class RefreshTokenRepository(BaseRepository[RefreshToken]):
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[RefreshToken]:
        query = select(self.model).filter(
            self.model.token == token,
            self.model.revoked == False,
            self.model.expires_at > datetime.now(timezone.utc)
        )
        result = await db.execute(query)
        return result.scalars().first()

class BusOperatorRepository(BaseRepository[BusOperator]):
    pass

class BusRepository(BaseRepository[Bus]):
    async def get_by_license_plate(self, db: AsyncSession, license_plate: str) -> Optional[Bus]:
        query = select(self.model).filter(self.model.license_plate == license_plate, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

    async def search_buses(self, db: AsyncSession, query_str: str) -> List[Bus]:
        query = select(self.model).filter(
            and_(
                or_(
                    self.model.bus_number.ilike(f"%{query_str}%"),
                    self.model.license_plate.ilike(f"%{query_str}%")
                ),
                self.model.deleted_at == None
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

class RouteRepository(BaseRepository[Route]):
    async def get_by_route_number(self, db: AsyncSession, route_number: str) -> Optional[Route]:
        query = select(self.model).filter(self.model.route_number == route_number, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

    async def search_routes(self, db: AsyncSession, query_str: str, ref_time_str: Optional[str] = None) -> List[Route]:
        # 1. Find all stops matching query_str
        stop_query = select(Stop).filter(Stop.name.ilike(f"%{query_str}%"), Stop.deleted_at == None)
        stop_res = await db.execute(stop_query)
        matching_stops = stop_res.scalars().all()
        matching_stop_ids = [s.id for s in matching_stops]

        # 2. Find routes associated with these stops via Timetable
        stop_route_ids = []
        if matching_stop_ids:
            tt_query = select(Timetable.route_id).filter(Timetable.stop_id.in_(matching_stop_ids))
            tt_res = await db.execute(tt_query)
            stop_route_ids = list(set(tt_res.scalars().all()))

        # 3. Find routes matching text directly (route_number, source, destination, description)
        text_query = select(self.model).filter(
            and_(
                or_(
                    self.model.route_number.ilike(f"%{query_str}%"),
                    self.model.description.ilike(f"%{query_str}%"),
                    self.model.source.ilike(f"%{query_str}%"),
                    self.model.destination.ilike(f"%{query_str}%")
                ),
                self.model.deleted_at == None
            )
        )
        text_res = await db.execute(text_query)
        matching_routes = {r.id: r for r in text_res.scalars().all()}

        # 4. Include routes that pass through the matching stops
        if stop_route_ids:
            stops_route_query = select(self.model).filter(self.model.id.in_(stop_route_ids), self.model.deleted_at == None)
            stops_route_res = await db.execute(stops_route_query)
            for r in stops_route_res.scalars().all():
                matching_routes[r.id] = r

        routes_list = list(matching_routes.values())

        # 5. Sort routes based on closest timetable time at matching stops (if applicable)
        if matching_stop_ids and routes_list:
            # Fetch all timetable entries for these routes at these stops
            all_tt_query = select(Timetable).filter(
                Timetable.route_id.in_([r.id for r in routes_list]),
                Timetable.stop_id.in_(matching_stop_ids)
            )
            all_tt_res = await db.execute(all_tt_query)
            all_tts = all_tt_res.scalars().all()

            # Group timetables by route_id
            route_tts = {}
            for tt in all_tts:
                route_tts.setdefault(tt.route_id, []).append(tt)

            # Parse reference time
            ref_time = None
            if ref_time_str:
                try:
                    parts = ref_time_str.split(':')
                    ref_time = time(int(parts[0]), int(parts[1]))
                except Exception:
                    pass
            
            if not ref_time:
                ref_time = datetime.now().time()
                
            now_m = ref_time.hour * 60 + ref_time.minute

            def get_min_time_diff(route_id):
                tts = route_tts.get(route_id, [])
                if not tts:
                    return 999999
                
                min_diff = 999999
                for tt in tts:
                    for t_val in [tt.arrival_time, tt.departure_time]:
                        if t_val:
                            tm = t_val.hour * 60 + t_val.minute
                            diff = abs(now_m - tm)
                            diff = min(diff, 1440 - diff)
                            if diff < min_diff:
                                min_diff = diff
                return min_diff

            routes_list.sort(key=lambda r: get_min_time_diff(r.id))

        return routes_list

class StopRepository(BaseRepository[Stop]):
    async def search_stops(self, db: AsyncSession, query_str: str) -> List[Stop]:
        query = select(self.model).filter(
            and_(
                self.model.name.ilike(f"%{query_str}%"),
                self.model.deleted_at == None
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def get_nearby_stops(self, db: AsyncSession, lat: float, lon: float, radius_km: float = 2.0) -> List[Stop]:
        # Simple bounding box estimate for SQL search
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * abs(func.cos(func.radians(lat))))
        
        query = select(self.model).filter(
            and_(
                self.model.latitude.between(lat - lat_delta, lat + lat_delta),
                self.model.longitude.between(lon - lon_delta, lon + lon_delta),
                self.model.deleted_at == None
            )
        )
        result = await db.execute(query)
        return result.scalars().all()

class RouteStopRepository(BaseRepository[RouteStop]):
    async def get_by_route(self, db: AsyncSession, route_id: uuid.UUID) -> List[RouteStop]:
        query = select(self.model).filter(self.model.route_id == route_id).order_by(self.model.sequence_order)
        result = await db.execute(query)
        return result.scalars().all()

class TimetableRepository(BaseRepository[Timetable]):
    async def get_by_route_and_stop(self, db: AsyncSession, route_id: uuid.UUID, stop_id: uuid.UUID) -> List[Timetable]:
        query = select(self.model).filter(
            self.model.route_id == route_id,
            self.model.stop_id == stop_id
        ).order_by(self.model.arrival_time)
        result = await db.execute(query)
        return result.scalars().all()

class PassengerReportRepository(BaseRepository[PassengerReport]):
    async def get_active_reports(self, db: AsyncSession, minutes: int = 30) -> List[PassengerReport]:
        from datetime import timedelta
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        query = select(self.model).filter(self.model.created_at >= time_threshold)
        result = await db.execute(query)
        return result.scalars().all()

class ChatRoomRepository(BaseRepository[ChatRoom]):
    async def get_by_route(self, db: AsyncSession, route_id: uuid.UUID) -> Optional[ChatRoom]:
        query = select(self.model).filter(self.model.route_id == route_id, self.model.deleted_at == None)
        result = await db.execute(query)
        return result.scalars().first()

class ChatMessageRepository(BaseRepository[ChatMessage]):
    async def get_messages(self, db: AsyncSession, chat_room_id: uuid.UUID, limit: int = 50) -> List[ChatMessage]:
        query = select(self.model).filter(self.model.chat_room_id == chat_room_id).order_by(self.model.created_at.desc()).limit(limit)
        result = await db.execute(query)
        # Reverse to get chronological order
        messages = result.scalars().all()
        messages.reverse()
        return messages

class AdvertisementRepository(BaseRepository[Advertisement]):
    async def get_active_ads(self, db: AsyncSession) -> List[Advertisement]:
        now = datetime.now(timezone.utc)
        query = select(self.model).filter(
            self.model.is_active == True,
            self.model.start_date <= now,
            self.model.end_date >= now,
            self.model.deleted_at == None
        )
        result = await db.execute(query)
        return result.scalars().all()

class NotificationRepository(BaseRepository[Notification]):
    pass

class NotificationHistoryRepository(BaseRepository[NotificationHistory]):
    async def get_unread(self, db: AsyncSession, user_id: uuid.UUID) -> List[NotificationHistory]:
        query = select(self.model).filter(
            self.model.user_id == user_id,
            self.model.is_read == False
        )
        result = await db.execute(query)
        return result.scalars().all()

class MLPredictionRepository(BaseRepository[MLPrediction]):
    pass

class AnalyticsLogRepository(BaseRepository[AnalyticsLog]):
    pass

class AuditLogRepository(BaseRepository[AuditLog]):
    pass

class ExtractedTimetableRepository(BaseRepository[ExtractedTimetable]):
    pass

# Singleton repository instances
role_repo = RoleRepository(Role)
user_repo = UserRepository(User)
token_repo = RefreshTokenRepository(RefreshToken)
operator_repo = BusOperatorRepository(BusOperator)
bus_repo = BusRepository(Bus)
route_repo = RouteRepository(Route)
stop_repo = StopRepository(Stop)
route_stop_repo = RouteStopRepository(RouteStop)
timetable_repo = TimetableRepository(Timetable)
report_repo = PassengerReportRepository(PassengerReport)
chat_room_repo = ChatRoomRepository(ChatRoom)
chat_msg_repo = ChatMessageRepository(ChatMessage)
ad_repo = AdvertisementRepository(Advertisement)
notification_repo = NotificationRepository(Notification)
notification_history_repo = NotificationHistoryRepository(NotificationHistory)
ml_prediction_repo = MLPredictionRepository(MLPrediction)
analytics_log_repo = AnalyticsLogRepository(AnalyticsLog)
audit_log_repo = AuditLogRepository(AuditLog)
extracted_timetable_repo = ExtractedTimetableRepository(ExtractedTimetable)
