from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import BookingCreate, BookingOut
from app.services import booking as booking_service

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    booking = booking_service.create_booking(db, user, payload)
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        centre_id=booking.centre_id,
        centre_test_id=booking.centre_test_id,
        appointment_at=booking.appointment_at,
        amount=booking.amount,
        status=booking.status.value,
        created_at=booking.created_at,
    )


@router.get("/", response_model=dict)
def list_bookings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    items, total = booking_service.list_user_bookings(db, user, skip, limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [
            BookingOut(
                id=b.id,
                user_id=b.user_id,
                centre_id=b.centre_id,
                centre_test_id=b.centre_test_id,
                appointment_at=b.appointment_at,
                amount=b.amount,
                status=b.status.value,
                created_at=b.created_at,
            ).model_dump(mode="json")
            for b in items
        ],
    }


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    booking = booking_service.get_user_booking(db, user, booking_id)
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        centre_id=booking.centre_id,
        centre_test_id=booking.centre_test_id,
        appointment_at=booking.appointment_at,
        amount=booking.amount,
        status=booking.status.value,
        created_at=booking.created_at,
    )


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BookingOut:
    booking = booking_service.cancel_booking(db, user, booking_id)
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        centre_id=booking.centre_id,
        centre_test_id=booking.centre_test_id,
        appointment_at=booking.appointment_at,
        amount=booking.amount,
        status=booking.status.value,
        created_at=booking.created_at,
    )
