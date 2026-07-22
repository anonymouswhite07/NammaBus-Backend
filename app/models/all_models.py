import uuid
from datetime import datetime, time
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, Time, Text, JSON, DateTime, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, BaseModelMixin

# Association table for Favourite Routes (Users <-> Routes)
favourite_routes = Table(
    "favourite_routes",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("route_id", ForeignKey("routes.id", ondelete="CASCADE"), primary_key=True),
)

class Role(Base, BaseModelMixin):
    __tablename__ = "roles"
    
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Relationships
    users: Mapped[List["User"]] = relationship(back_populates="role")

class User(Base, BaseModelMixin):
    __tablename__ = "users"
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Optional for OAuth2/Firebase users
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    firebase_uid: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    
    # Relationships
    role: Mapped["Role"] = relationship(back_populates="users")
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[List["PassengerReport"]] = relationship(back_populates="user")
    chat_messages: Mapped[List["ChatMessage"]] = relationship(back_populates="user")
    favorites: Mapped[List["Route"]] = relationship(secondary=favourite_routes, back_populates="favorited_by")
    notification_history: Mapped[List["NotificationHistory"]] = relationship(back_populates="user")
    audit_logs: Mapped[List["AuditLog"]] = relationship(back_populates="user")

class RefreshToken(Base, BaseModelMixin):
    __tablename__ = "refresh_tokens"
    
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")

class BusOperator(Base, BaseModelMixin):
    __tablename__ = "bus_operators"
    
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    contact_info: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Relationships
    buses: Mapped[List["Bus"]] = relationship(back_populates="operator")

class Bus(Base, BaseModelMixin):
    __tablename__ = "buses"
    
    bus_number: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    license_plate: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=55)
    status: Mapped[str] = mapped_column(String(50), default="ON_TIME") # ON_TIME, DELAYED, INACTIVE
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    operator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bus_operators.id"), nullable=False)
    active_route_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("routes.id"), nullable=True)
    
    # Relationships
    operator: Mapped["BusOperator"] = relationship(back_populates="buses")
    active_route: Mapped[Optional["Route"]] = relationship(back_populates="buses")

class Route(Base, BaseModelMixin):
    __tablename__ = "routes"
    
    route_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    fare: Mapped[float] = mapped_column(Float, default=0.0)
    frequency: Mapped[str] = mapped_column(String(50), default="15 mins")
    trip_duration: Mapped[str] = mapped_column(String(50), default="45 mins")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    buses: Mapped[List["Bus"]] = relationship(back_populates="active_route")
    route_stops: Mapped[List["RouteStop"]] = relationship(back_populates="route", cascade="all, delete-orphan")
    timetables: Mapped[List["Timetable"]] = relationship(back_populates="route", cascade="all, delete-orphan")
    reports: Mapped[List["PassengerReport"]] = relationship(back_populates="route")
    chat_room: Mapped[Optional["ChatRoom"]] = relationship(back_populates="route", cascade="all, delete-orphan")
    favorited_by: Mapped[List["User"]] = relationship(secondary=favourite_routes, back_populates="favorites")

class Stop(Base, BaseModelMixin):
    __tablename__ = "stops"
    
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Relationships
    route_stops: Mapped[List["RouteStop"]] = relationship(back_populates="stop", cascade="all, delete-orphan")
    timetables: Mapped[List["Timetable"]] = relationship(back_populates="stop")
    reports: Mapped[List["PassengerReport"]] = relationship(back_populates="stop")

class RouteStop(Base, BaseModelMixin):
    __tablename__ = "route_stops"
    
    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    stop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Relationships
    route: Mapped["Route"] = relationship(back_populates="route_stops")
    stop: Mapped["Stop"] = relationship(back_populates="route_stops")

class Timetable(Base, BaseModelMixin):
    __tablename__ = "timetables"
    
    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False)
    stop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"), nullable=False)
    arrival_time: Mapped[time] = mapped_column(Time, nullable=False)
    departure_time: Mapped[time] = mapped_column(Time, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(20), default="WEEKDAY") # WEEKDAY, SATURDAY, SUNDAY
    
    # Relationships
    route: Mapped["Route"] = relationship(back_populates="timetables")
    stop: Mapped["Stop"] = relationship(back_populates="timetables")

class PassengerReport(Base, BaseModelMixin):
    __tablename__ = "passenger_reports"
    
    report_type: Mapped[str] = mapped_column(String(50), nullable=False) # ARRIVED, LEFT, HEAVY_TRAFFIC, CROWDED, SEATS_AVAILABLE, ACCIDENT, BREAKDOWN
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    crowd_level: Mapped[Optional[str]] = mapped_column(String(50)) # LOW, MEDIUM, HIGH
    delay_minutes: Mapped[int] = mapped_column(Integer, default=0)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id"), nullable=False)
    stop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stops.id"), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="reports")
    route: Mapped["Route"] = relationship(back_populates="reports")
    stop: Mapped["Stop"] = relationship(back_populates="reports")

class ChatRoom(Base, BaseModelMixin):
    __tablename__ = "chat_rooms"
    
    route_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relationships
    route: Mapped["Route"] = relationship(back_populates="chat_room")
    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="chat_room", cascade="all, delete-orphan")

class ChatMessage(Base, BaseModelMixin):
    __tablename__ = "chat_messages"
    
    message: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="TEXT") # TEXT, IMAGE
    
    chat_room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Relationships
    chat_room: Mapped["ChatRoom"] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="chat_messages")

class Advertisement(Base, BaseModelMixin):
    __tablename__ = "advertisements"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    ad_type: Mapped[str] = mapped_column(String(50), nullable=False) # BANNER, NATIVE, SPONSORED_ROUTE, NEARBY_BUSINESS
    image_url: Mapped[Optional[str]] = mapped_column(String(512))
    target_url: Mapped[Optional[str]] = mapped_column(String(512))
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Stats
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0.0)

class Notification(Base, BaseModelMixin):
    __tablename__ = "notifications"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False) # BUS_DELAY, BUS_ARRIVING, COMMUNITY_UPDATE, EMERGENCY_ALERT
    
    # Relationships
    history: Mapped[List["NotificationHistory"]] = relationship(back_populates="notification", cascade="all, delete-orphan")

class NotificationHistory(Base, BaseModelMixin):
    __tablename__ = "notification_history"
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    notification_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    notification: Mapped["Notification"] = relationship(back_populates="history")
    user: Mapped["User"] = relationship(back_populates="notification_history")

class MLPrediction(Base, BaseModelMixin):
    __tablename__ = "ml_predictions"
    
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False) # ETA, CROWD, POSITION
    target_id: Mapped[str] = mapped_column(String(100), nullable=False) # RouteId / StopId / BusId
    prediction_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    input_features: Mapped[dict] = mapped_column(JSON, nullable=False)

class AnalyticsLog(Base, BaseModelMixin):
    __tablename__ = "analytics_logs"
    
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False) # ROUTE_SEARCH, CHAT_JOIN, AD_CLICK, REPORT_SUBMIT
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

class AuditLog(Base, BaseModelMixin):
    __tablename__ = "audit_logs"
    
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="audit_logs")

class ExtractedTimetable(Base, BaseModelMixin):
    __tablename__ = "extracted_timetables"

    sector: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    serial_number: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_time: Mapped[str] = mapped_column(String(50), nullable=False)
    departure_time: Mapped[str] = mapped_column(String(50), nullable=False)
    arrival_time_normalized: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    departure_time_normalized: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    route_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    operator: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(Boolean, default=False)

