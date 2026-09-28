from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import PaymentCreate, PaymentOut, WebhookPayload, WebhookResponse
from app.services import payment as payment_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PaymentOut:
    payment = payment_service.process_payment(db, user, payload)
    return PaymentOut(
        id=payment.id,
        booking_id=payment.booking_id,
        provider_payment_id=payment.provider_payment_id,
        status=payment.status.value,
        amount=payment.amount,
        created_at=payment.created_at,
    )


@router.post("/webhook/", response_model=WebhookResponse)
def payment_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None, alias="X-Webhook-Secret"),
) -> WebhookResponse:
    settings = get_settings()
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    result = payment_service.process_webhook(db, payload)
    return WebhookResponse(**result)
