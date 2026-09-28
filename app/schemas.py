from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: list


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CentreTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    centre_id: UUID
    name: str
    price: Decimal
    is_active: bool


class CentreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    location: str


class CentreDetailOut(CentreOut):
    tests: list[CentreTestOut] = []


class BookingCreate(BaseModel):
    centre_id: UUID
    centre_test_id: UUID
    appointment_at: datetime


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    centre_id: UUID
    centre_test_id: UUID
    appointment_at: datetime
    amount: Decimal
    status: str
    created_at: datetime


class PaymentCreate(BaseModel):
    booking_id: UUID
    force_status: str | None = Field(
        default=None,
        description="Optional SUCCESS or FAILED for deterministic testing",
    )


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    booking_id: UUID
    provider_payment_id: str
    status: str
    amount: Decimal
    created_at: datetime


class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, max_length=255)
    provider_payment_id: str = Field(min_length=1, max_length=255)
    status: str = Field(description="SUCCESS or FAILED")


class WebhookResponse(BaseModel):
    status: str
    message: str
    payment_id: UUID | None = None
    booking_status: str | None = None
