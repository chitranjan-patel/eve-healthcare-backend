from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, CentreTest, DiagnosticCentre, User
from app.schemas import BookingCreate


def create_booking(db: Session, user: User, payload: BookingCreate) -> Booking:
    appointment_at = payload.appointment_at
    if appointment_at.tzinfo is None:
        appointment_at = appointment_at.replace(tzinfo=timezone.utc)

    if appointment_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="appointment_at must be in the future",
        )

    centre = db.get(DiagnosticCentre, payload.centre_id)
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic centre not found")

    centre_test = db.get(CentreTest, payload.centre_test_id)
    if centre_test is None or centre_test.centre_id != payload.centre_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Diagnostic test not found for this centre",
        )
    if not centre_test.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Diagnostic test is not available")

    booking = Booking(
        user_id=user.id,
        centre_id=centre.id,
        centre_test_id=centre_test.id,
        appointment_at=appointment_at,
        amount=centre_test.price,
        status=BookingStatus.PENDING,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_user_booking(db: Session, user: User, booking_id: UUID) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this booking")
    return booking


def cancel_booking(db: Session, user: User, booking_id: UUID) -> Booking:
    booking = get_user_booking(db, user, booking_id)
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel booking in status {booking.status.value}",
        )
    booking.status = BookingStatus.CANCELLED
    db.commit()
    db.refresh(booking)
    return booking


def list_user_bookings(db: Session, user: User, skip: int, limit: int) -> tuple[list[Booking], int]:
    query = db.query(Booking).filter(Booking.user_id == user.id).order_by(Booking.created_at.desc())
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return items, total
