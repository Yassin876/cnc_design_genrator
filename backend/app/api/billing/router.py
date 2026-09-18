from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
import uuid
from pydantic import BaseModel

from backend.app.db.session import get_db
from backend.app.api.auth.router import get_current_user
from backend.app.schemas.user import UserRead
from backend.app.schemas.payment import (
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentMethodListResponse,
)
from backend.app.services.subscription_service import SubscriptionService
from backend.app.services.payment_service import PaymentService
from backend.app.models.payment import Payment
from backend.app.models.payment_method import PaymentMethod
from backend.app.core.config import settings

from backend.app.services.paddle_service import PaddleService
from fastapi import Request

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])
security_scheme = HTTPBearer(auto_error=False)


def require_admin(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    """FastAPI security dependency ensuring the caller has administrator privileges."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required to access this resource.",
        )
    return current_user


class PaymentRequestPayload(BaseModel):
    plan_requested: str
    method: str  # 'cash' | 'instapay'
    proof_reference: Optional[str] = None


class MockCheckoutPayload(BaseModel):
    plan_requested: str


class ApprovePaymentPayload(BaseModel):
    admin_notes: Optional[str] = None


class RejectPaymentPayload(BaseModel):
    reason: Optional[str] = None


class CreateCheckoutPayload(BaseModel):
    plan_id: str


# ── PADDLE BILLING INTEGRATION ENDPOINTS ─────────────────────────────────────

@router.get("/paddle/config")
def get_paddle_public_config():
    """
    Returns public Paddle configuration (environment, client-side token, and price IDs).
    Never exposes backend secret keys.
    """
    return PaddleService.get_public_config()


@router.post("/paddle/create-checkout")
def create_paddle_checkout_session(
    payload: CreateCheckoutPayload,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Creates a secure Paddle Hosted Checkout URL for desktop/external browser checkout.
    """
    user = SubscriptionService.get_or_init_user(db, current_user.id)
    try:
        return PaddleService.create_checkout_url(user, payload.plan_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/paddle/webhook")
async def paddle_webhook_receiver(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receives and processes official Paddle webhook notifications.
    Enforces HMAC-SHA256 Paddle-Signature verification and idempotency.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("Paddle-Signature") or request.headers.get("paddle-signature")

    success, msg, details = PaddleService.process_webhook_event(db, raw_body, signature_header)
    if not success:
        status_code = details.get("status", status.HTTP_400_BAD_REQUEST)
        raise HTTPException(status_code=status_code, detail=msg)

    return {"success": True, "message": msg, "details": details}


@router.get("/paddle/subscription")
def get_user_paddle_subscription(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns Paddle subscription status and customer details for current authenticated user.
    """
    status_data = SubscriptionService.get_subscription_status(db, current_user.id)
    return {
        "user_id": current_user.id,
        "plan": status_data.get("plan"),
        "paddle_customer_id": status_data.get("paddle_customer_id"),
        "paddle_subscription_id": status_data.get("paddle_subscription_id"),
        "subscription_status": status_data.get("subscription_status"),
        "next_billing_date": status_data.get("next_billing_date"),
        "cancel_url": status_data.get("cancel_url"),
        "update_url": status_data.get("update_url"),
    }


@router.get("/config")
def get_payment_configuration():
    """Returns available payment options, account details, instructions, and placeholder warnings."""
    return PaymentService.get_payment_config()


@router.get("/status")
def get_billing_status(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns current user subscription tier, rolling cycle dates, and usage stats from database.
    """
    return SubscriptionService.get_subscription_status(db, current_user.id)


# ── PAYMENT METHODS (Secure Tokenized Vault) ──────────────────────────────────

@router.get("/payment-methods", response_model=PaymentMethodListResponse)
def get_payment_methods(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns saved tokenized payment methods for the authenticated user.
    Never exposes plain credit card numbers; only provider tokens, brand, and last 4 digits.
    """
    methods = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.user_id == current_user.id)
        .order_by(PaymentMethod.is_default.desc(), PaymentMethod.created_at.desc())
        .all()
    )
    return {
        "payment_methods": methods,
        "count": len(methods),
    }


@router.post("/payment-methods", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED)
def add_payment_method(
    payload: PaymentMethodCreate,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Securely registers a payment method token generated by a client-side payment gateway SDK.
    Stores only the token, brand, and last 4 digits (PCI-DSS compliant).
    """
    existing_count = db.query(PaymentMethod).filter(PaymentMethod.user_id == current_user.id).count()

    # If first payment method or payload specifies default, make it default
    is_default = payload.is_default or existing_count == 0

    if is_default:
        db.query(PaymentMethod).filter(PaymentMethod.user_id == current_user.id).update(
            {"is_default": False}
        )

    new_method = PaymentMethod(
        user_id=current_user.id,
        provider=payload.provider,
        payment_token=payload.payment_token,
        brand=payload.brand.lower(),
        last4=payload.last4,
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        holder_name=payload.holder_name,
        is_default=is_default,
    )
    db.add(new_method)
    db.commit()
    db.refresh(new_method)
    return new_method


@router.delete("/payment-methods/{payment_method_id}")
def delete_payment_method(
    payment_method_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a saved payment method belonging to the authenticated user."""
    method = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.id == payment_method_id, PaymentMethod.user_id == current_user.id)
        .first()
    )
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found or unauthorized.",
        )

    was_default = method.is_default
    db.delete(method)
    db.commit()

    # If deleted was default, make the most recent one default if any exists
    if was_default:
        remaining = (
            db.query(PaymentMethod)
            .filter(PaymentMethod.user_id == current_user.id)
            .order_by(PaymentMethod.created_at.desc())
            .first()
        )
        if remaining:
            remaining.is_default = True
            db.commit()

    return {"success": True, "message": "Payment method removed successfully."}


@router.patch("/payment-methods/{payment_method_id}/default", response_model=PaymentMethodRead)
def set_default_payment_method(
    payment_method_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sets the designated payment method as the primary/default for the user."""
    method = (
        db.query(PaymentMethod)
        .filter(PaymentMethod.id == payment_method_id, PaymentMethod.user_id == current_user.id)
        .first()
    )
    if not method:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment method not found or unauthorized.",
        )

    db.query(PaymentMethod).filter(PaymentMethod.user_id == current_user.id).update(
        {"is_default": False}
    )
    method.is_default = True
    db.commit()
    db.refresh(method)
    return method


# ── MANUAL PAYMENTS & CHECKOUT ────────────────────────────────────────────────

@router.post("/payment/mock-checkout")
async def mock_checkout_dev(
    payload: MockCheckoutPayload,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Development-only instant plan upgrade without manual admin approval."""
    return await PaymentService.process_mock_checkout(
        db=db,
        user_id=current_user.id,
        plan_requested=payload.plan_requested,
    )


@router.post("/payment/request")
def submit_payment_request(
    payload: PaymentRequestPayload,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits a manual payment request (InstaPay or Cash) with proof reference code."""
    payment = PaymentService.create_payment_request(
        db=db,
        user_id=current_user.id,
        plan_requested=payload.plan_requested,
        method=payload.method,
        proof_reference=payload.proof_reference,
    )
    return {
        "success": True,
        "message": "Payment request submitted successfully. Awaiting administrative review.",
        "payment": {
            "id": payment.id,
            "plan_requested": payment.plan_requested,
            "amount": payment.amount,
            "currency": payment.currency,
            "method": payment.method,
            "proof_reference": payment.proof_reference,
            "status": payment.status,
            "created_at": payment.created_at.isoformat(),
        },
    }


@router.post("/payment/upload-proof")
async def upload_payment_proof_file(
    file: UploadFile = File(...),
    plan_requested: str = Form(...),
    method: str = Form(...),
    proof_reference: Optional[str] = Form(None),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Uploads a receipt image and creates a pending payment request."""
    upload_dir = os.path.join(settings.UPLOAD_DIR, "payment_proofs")
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
    safe_name = f"proof_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}{file_ext}"
    dest_path = os.path.join(upload_dir, safe_name)

    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    payment = PaymentService.create_payment_request(
        db=db,
        user_id=current_user.id,
        plan_requested=plan_requested,
        method=method,
        proof_reference=proof_reference or f"Receipt file: {file.filename}",
        proof_image_path=dest_path,
    )

    return {
        "success": True,
        "message": "Payment receipt uploaded and submitted for review.",
        "payment_id": payment.id,
        "proof_image_path": dest_path,
    }


@router.get("/payment/history")
def get_my_payment_history(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns payment requests history for the logged-in user."""
    payments = PaymentService.get_user_payments(db, current_user.id)
    return {
        "payments": [
            {
                "id": p.id,
                "plan_requested": p.plan_requested,
                "amount": p.amount,
                "currency": p.currency,
                "method": p.method,
                "proof_reference": p.proof_reference,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "admin_notes": p.admin_notes,
            }
            for p in payments
        ]
    }


# ── ADMIN ENDPOINTS (Protected with require_admin) ───────────────────────────

@router.get("/admin/payments")
def list_admin_payments(
    status_filter: Optional[str] = Query(None),
    admin_user: UserRead = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: lists payment requests filtered by status."""
    payments = PaymentService.list_all_payments(db, status_filter)
    return {
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
                "user_name": p.user_name,
                "user_email": p.user_email,
                "plan_requested": p.plan_requested,
                "amount": p.amount,
                "currency": p.currency,
                "method": p.method,
                "proof_reference": p.proof_reference,
                "proof_image_path": p.proof_image_path,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "reviewed_at": p.reviewed_at.isoformat() if p.reviewed_at else None,
                "reviewed_by": p.reviewed_by,
                "admin_notes": p.admin_notes,
            }
            for p in payments
        ]
    }


@router.post("/admin/payments/{payment_id}/approve")
def approve_admin_payment(
    payment_id: str,
    payload: Optional[ApprovePaymentPayload] = None,
    admin_user: UserRead = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: approves payment, updates target user plan, and resets 30-day cycle."""
    notes = payload.admin_notes if payload else None
    return PaymentService.approve_payment(db, payment_id, admin_user.id, admin_notes=notes)


@router.post("/admin/payments/{payment_id}/reject")
def reject_admin_payment(
    payment_id: str,
    payload: Optional[RejectPaymentPayload] = None,
    admin_user: UserRead = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only: rejects payment with reason."""
    reason = payload.reason if payload else None
    return PaymentService.reject_payment(db, payment_id, admin_user.id, reason=reason)
