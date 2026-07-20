import uuid
from datetime import datetime, time
from typing import Any, List, Optional, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, EmailStr, Field

T = TypeVar("T")

# Generic Standard Envelope Response
class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = ""
    data: Optional[T] = None

# Token Schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

# Role Schemas
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleResponse(RoleBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str

class UserCreate(UserBase):
    password: str
    role_name: str = "Passenger"

class UserRegister(UserBase):
    password: str

class UserFirebaseCreate(UserBase):
    firebase_token: str
    role_name: str = "Passenger"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    role_id: Optional[uuid.UUID] = None

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    role: RoleResponse
    
    model_config = ConfigDict(from_attributes=True)

# Bus Operator Schemas
class BusOperatorBase(BaseModel):
    name: str
    contact_info: Optional[str] = None

class BusOperatorCreate(BusOperatorBase):
    pass

class BusOperatorResponse(BusOperatorBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

# Bus Schemas
class BusBase(BaseModel):
    bus_number: str
    license_plate: str
    capacity: int = 55
    status: str = "ON_TIME"

class BusCreate(BusBase):
    operator_id: uuid.UUID
    active_route_id: Optional[uuid.UUID] = None

class BusUpdate(BaseModel):
    bus_number: Optional[str] = None
    license_plate: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    active_route_id: Optional[uuid.UUID] = None

class BusResponse(BusBase):
    id: uuid.UUID
    is_active: bool
    operator_id: uuid.UUID
    active_route_id: Optional[uuid.UUID] = None
    
    model_config = ConfigDict(from_attributes=True)

# Route Schemas
class RouteBase(BaseModel):
    route_number: str
    source: str
    destination: str
    description: str
    fare: float = 0.0
    frequency: str = "15 mins"
    trip_duration: str = "45 mins"

class RouteCreate(RouteBase):
    pass

class RouteUpdate(BaseModel):
    route_number: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    description: Optional[str] = None
    fare: Optional[float] = None
    frequency: Optional[str] = None
    trip_duration: Optional[str] = None
    is_active: Optional[bool] = None

class RouteResponse(RouteBase):
    id: uuid.UUID
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# Stop Schemas
class StopBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    address: Optional[str] = None

class StopCreate(StopBase):
    pass

class StopResponse(StopBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

# Route Stop Junction Schemas
class RouteStopCreate(BaseModel):
    stop_id: uuid.UUID
    sequence_order: int

class RouteStopResponse(BaseModel):
    id: uuid.UUID
    route_id: uuid.UUID
    stop: StopResponse
    sequence_order: int
    
    model_config = ConfigDict(from_attributes=True)

# Timetable Schemas
class TimetableBase(BaseModel):
    arrival_time: time
    departure_time: time
    day_of_week: str = "WEEKDAY"

class TimetableCreate(TimetableBase):
    route_id: uuid.UUID
    stop_id: uuid.UUID

class TimetableResponse(TimetableBase):
    id: uuid.UUID
    route_id: uuid.UUID
    stop_id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

# Passenger Report Schemas
class PassengerReportBase(BaseModel):
    report_type: str
    latitude: float
    longitude: float
    crowd_level: Optional[str] = None
    delay_minutes: int = 0

class PassengerReportCreate(PassengerReportBase):
    route_id: uuid.UUID
    stop_id: uuid.UUID

class PassengerReportResponse(PassengerReportBase):
    id: uuid.UUID
    user_id: uuid.UUID
    route_id: uuid.UUID
    stop_id: uuid.UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Chat Messages Schemas
class ChatMessageBase(BaseModel):
    message: str
    message_type: str = "TEXT"

class ChatMessageCreate(ChatMessageBase):
    chat_room_id: uuid.UUID

class ChatMessageResponse(ChatMessageBase):
    id: uuid.UUID
    chat_room_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# Chat Room Schemas
class ChatRoomResponse(BaseModel):
    id: uuid.UUID
    route_id: uuid.UUID
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

# Advertisement Schemas
class AdvertisementBase(BaseModel):
    title: str
    content: str
    ad_type: str
    image_url: Optional[str] = None
    target_url: Optional[str] = None
    start_date: datetime
    end_date: datetime

class AdvertisementCreate(AdvertisementBase):
    pass

class AdvertisementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    ad_type: Optional[str] = None
    image_url: Optional[str] = None
    target_url: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class AdvertisementResponse(AdvertisementBase):
    id: uuid.UUID
    is_active: bool
    impressions: int
    clicks: int
    revenue: float
    
    model_config = ConfigDict(from_attributes=True)

# Notification Schemas
class NotificationBase(BaseModel):
    title: str
    body: str
    notification_type: str

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: uuid.UUID
    
    model_config = ConfigDict(from_attributes=True)

class NotificationHistoryResponse(BaseModel):
    id: uuid.UUID
    notification: NotificationResponse
    is_read: bool
    read_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)

# ML Prediction Schemas
class MLPredictionResponse(BaseModel):
    id: uuid.UUID
    model_name: str
    model_version: str
    prediction_type: str
    target_id: str
    prediction_value: Any
    input_features: Any
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
