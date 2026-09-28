import hashlib
import json
import random
import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.logging_config import get_logger
from app.models import Booking, BookingStatus, Payment, PaymentStatus, PaymentWebhookEvent, User
from app.schemas import PaymentCreate, WebhookPayload
from app.services.booking import get_user_booking

logger = get_logger(__name__)


def _map_payment_to_booking_status(payment_status: PaymentStatus) -> BookingStatus:
    if payment_status == PaymentStatus.SUCCESS:
        return BookingStatus.CONFIRMED
    return BookingStatus.FAILED


def process_payment(db: Session, user: User, payload: PaymentCreate) -> Payment:
    booking = get_user_booking(db, user, payload.booking_id)

    if booking.status != BookingStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot pay for booking in status {booking.status.value}",
        )

    existing = db.query(Payment).filter(Payment.booking_id == booking.id).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already exists for this booking")

    settings = get_settings()
    if payload.force_status:
        force = payload.force_status.upper()
        if force not in {PaymentStatus.SUCCESS.value, PaymentStatus.FAILED.value}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="force_status must be SUCCESS or FAILED",
            )
        payment_status = PaymentStatus(force)
    else:
        payment_status = (
            PaymentStatus.SUCCESS
            if random.random() < settings.payment_success_rate
            else PaymentStatus.FAILED
        )

    payment = Payment(
        booking_id=booking.id,
        provider_payment_id=f"pay_{uuid.uuid4().hex}",
        status=payment_status,
        amount=booking.amount,
    )
    booking.status = _map_payment_to_booking_status(payment_status)

    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(
        "payment_processed",
        payment_id=str(payment.id),
        booking_id=str(booking.id),
        status=payment_status.value,
    )
    return payment


def process_webhook(db: Session, payload: WebhookPayload) -> dict:
    status_value = payload.status.upper()
    if status_value not in {PaymentStatus.SUCCESS.value, PaymentStatus.FAILED.value}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be SUCCESS or FAILED",
        )
    new_status = PaymentStatus(status_value)

    existing_event = db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.event_id == payload.event_id).first()
    if existing_event is not None:
        payment = db.get(Payment, existing_event.payment_id)
        booking = db.get(Booking, payment.booking_id) if payment else None
        logger.info("webhook_duplicate", event_id=payload.event_id)
        return {
            "status": "already_processed",
            "message": "Duplicate webhook event ignored",
            "payment_id": payment.id if payment else None,
            "booking_status": booking.status.value if booking else None,
        }

    payment = db.query(Payment).filter(Payment.provider_payment_id == payload.provider_payment_id).first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    booking = db.get(Booking, payment.booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    raw = json.dumps(payload.model_dump(), sort_keys=True)
    payload_hash = hashlib.sha256(raw.encode()).hexdigest()

    event = PaymentWebhookEvent(
        event_id=payload.event_id,
        payment_id=payment.id,
        payload_hash=payload_hash,
        raw_payload=raw,
    )
    db.add(event)

    payment.status = new_status
    if booking.status != BookingStatus.CANCELLED:
        booking.status = _map_payment_to_booking_status(new_status)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        # Race: another request inserted the same event_id
        existing_event = (
            db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.event_id == payload.event_id).first()
        )
        payment = db.get(Payment, existing_event.payment_id) if existing_event else payment
        booking = db.get(Booking, payment.booking_id) if payment else booking
        return {
            "status": "already_processed",
            "message": "Duplicate webhook event ignored",
            "payment_id": payment.id if payment else None,
            "booking_status": booking.status.value if booking else None,
        }

    db.refresh(payment)
    db.refresh(booking)
    logger.info(
        "webhook_processed",
        event_id=payload.event_id,
        payment_id=str(payment.id),
        booking_status=booking.status.value,
    )
    return {
        "status": "processed",
        "message": "Webhook applied",
        "payment_id": payment.id,
        "booking_status": booking.status.value,
    }
