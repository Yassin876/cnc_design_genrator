import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.models.payment import Payment
from backend.app.services.subscription_service import PLAN_PRICING, PLAN_LIMITS, SubscriptionService
from backend.app.core.config import settings

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "payment_config.json"))


class MockPaymentProvider:
    """Instant checkout for local development — no external payment gateway."""

    async def process_payment(self, user_id: str, amount: float, plan: str) -> Dict[str, Any]:
        return {
            "status": "success",
            "transaction_id": f"mock_{uuid.uuid4()}",
            "user_id": user_id,
            "amount": amount,
            "plan": plan,
        }


class PaymentService:
    @staticmethod
    def get_payment_config() -> Dict[str, Any]:
        """Loads payment methods configuration and placeholder instructions."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading payment config: {e}")
        
        # Fallback default
        return {
            "instapay": {
                "enabled": True,
                "account_name": "Anti Design Engineering Ltd (Demo / Placeholder)",
                "account_handle_or_number": "antidesign@instapay (Placeholder)",
                "phone_number": "+20 100 000 0000 (Placeholder)",
                "instructions": "Transfer the exact plan amount to the InstaPay address above and enter the transaction reference number or upload the receipt.",
                "is_placeholder": True
            },
            "cash": {
                "enabled": True,
                "contact_person": "Anti Design Representative (Placeholder)",
                "contact_phone": "+20 100 000 0000 (Placeholder)",
                "office_address": "Engineering Studio HQ, Cairo (Placeholder)",
                "instructions": "Contact representative to arrange cash collection or deposit, then enter the cash receipt reference code.",
                "is_placeholder": True
            },
            "payment_gateway": {
                "provider": "manual",
                "provider_notes": "Pluggable provider interface ready for Paymob/Kashier integration",
                "api_key": "",
                "api_url": "",
                "webhook_secret": ""
            }
        }

    @classmethod
    async def process_mock_checkout(
        cls,
        db: Session,
        user_id: str,
        plan_requested: str,
        admin_user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dev-only: simulates an instant successful payment and upgrades the user's plan.
        """
        if settings.ENVIRONMENT not in ("development", "dev", "local"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Mock checkout is only available in development.",
            )

        plan_key = plan_requested.lower()
        if plan_key not in PLAN_PRICING or plan_key == "free":
            raise HTTPException(status_code=400, detail=f"Invalid paid plan: '{plan_requested}'")

        amount = PLAN_PRICING[plan_key]
        provider = MockPaymentProvider()
        gateway_result = await provider.process_payment(user_id, amount, plan_key)

        user = SubscriptionService.get_or_init_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        payment = Payment(
            id=str(uuid.uuid4()),
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            plan_requested=plan_key,
            amount=amount,
            currency="USD",
            method="mock",
            proof_reference=gateway_result["transaction_id"],
            status="approved",
            created_at=datetime.utcnow(),
            reviewed_at=datetime.utcnow(),
            reviewed_by=admin_user_id or user.id,
            admin_notes="Auto-approved via MockPaymentProvider (development)",
        )
        db.add(payment)

        now = datetime.utcnow()
        user.plan = plan_key
        user.requests_used_current_cycle = 0
        user.cycle_start_date = now
        user.cycle_end_date = now + timedelta(days=30)

        db.commit()
        db.refresh(payment)
        db.refresh(user)

        return {
            "success": True,
            "message": f"Mock payment succeeded. Plan upgraded to '{plan_key}'.",
            "gateway": gateway_result,
            "payment_id": payment.id,
            "new_plan": user.plan,
            "requests_limit": PLAN_LIMITS.get(user.plan, 15),
        }

    @classmethod
    def create_payment_request(
        cls,
        db: Session,
        user_id: str,
        plan_requested: str,
        method: str,
        proof_reference: Optional[str] = None,
        proof_image_path: Optional[str] = None
    ) -> Payment:
        """Creates a pending payment request submitted by a user."""
        user = SubscriptionService.get_or_init_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        plan_key = plan_requested.lower()
        if plan_key not in PLAN_PRICING or plan_key == "free":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid plan for paid subscription: '{plan_requested}'. Choose from 'pro', 'pro_plus', or 'business'."
            )

        method_key = method.lower()
        if method_key not in ["cash", "instapay"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid payment method: '{method}'. Supported methods are 'cash' and 'instapay'."
            )

        if not proof_reference and not proof_image_path:
            raise HTTPException(
                status_code=400,
                detail="Please provide a payment reference number, transaction code, or receipt attachment."
            )

        amount = PLAN_PRICING[plan_key]

        payment = Payment(
            id=str(uuid.uuid4()),
            user_id=user.id,
            user_name=user.name,
            user_email=user.email,
            plan_requested=plan_key,
            amount=amount,
            currency="USD",
            method=method_key,
            proof_reference=proof_reference,
            proof_image_path=proof_image_path,
            status="pending_approval",
            created_at=datetime.utcnow()
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)
        return payment

    @classmethod
    def get_user_payments(cls, db: Session, user_id: str) -> List[Payment]:
        """Returns payment history for a user."""
        return db.query(Payment).filter(Payment.user_id == user_id).order_by(Payment.created_at.desc()).all()

    @classmethod
    def list_all_payments(cls, db: Session, status_filter: Optional[str] = None) -> List[Payment]:
        """Admin helper to list payments."""
        query = db.query(Payment)
        if status_filter:
            query = query.filter(Payment.status == status_filter)
        return query.order_by(Payment.created_at.desc()).all()

    @classmethod
    def approve_payment(
        cls,
        db: Session,
        payment_id: str,
        admin_user_id: str,
        admin_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approves a pending payment:
        1. Marks payment as approved.
        2. Upgrades user's plan.
        3. Resets user's requests_used_current_cycle = 0.
        4. Sets cycle_start_date = now and cycle_end_date = now + 30 days.
        """
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment request not found")

        if payment.status == "approved":
            raise HTTPException(status_code=400, detail="Payment has already been approved")

        user = db.query(User).filter(User.id == payment.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Target user for this payment no longer exists")

        now = datetime.utcnow()
        # Update user subscription
        user.plan = payment.plan_requested
        user.requests_used_current_cycle = 0
        user.cycle_start_date = now
        user.cycle_end_date = now + timedelta(days=30)

        # Update payment record
        payment.status = "approved"
        payment.reviewed_at = now
        payment.reviewed_by = admin_user_id
        if admin_notes:
            payment.admin_notes = admin_notes

        db.commit()
        db.refresh(payment)
        db.refresh(user)

        return {
            "success": True,
            "message": f"Payment approved. User '{user.email}' upgraded to '{payment.plan_requested.title()}' plan with a new 30-day billing cycle.",
            "payment_id": payment.id,
            "user_id": user.id,
            "new_plan": user.plan,
            "requests_limit": PLAN_LIMITS.get(user.plan, 15),
            "cycle_start_date": user.cycle_start_date.isoformat(),
            "cycle_end_date": user.cycle_end_date.isoformat()
        }

    @classmethod
    def reject_payment(
        cls,
        db: Session,
        payment_id: str,
        admin_user_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Rejects a payment request with notes/reason."""
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            raise HTTPException(status_code=404, detail="Payment request not found")

        now = datetime.utcnow()
        payment.status = "rejected"
        payment.reviewed_at = now
        payment.reviewed_by = admin_user_id
        payment.admin_notes = reason or "Payment rejected by admin review."

        db.commit()
        db.refresh(payment)

        return {
            "success": True,
            "message": f"Payment request '{payment_id}' has been rejected.",
            "payment_id": payment.id,
            "status": "rejected",
            "admin_notes": payment.admin_notes
        }
