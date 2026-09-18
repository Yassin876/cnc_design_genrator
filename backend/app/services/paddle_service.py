import hmac
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.user import User
from backend.app.models.paddle_event import PaddleWebhookEvent

logger = logging.getLogger("cnc_studio.billing")


class PaddleService:
    @classmethod
    def get_price_plan_map(cls) -> Dict[str, str]:
        """Maps Paddle Price IDs to system plan tiers."""
        return {
            settings.PADDLE_PRICE_PRO: "pro",
            settings.PADDLE_PRICE_PRO_PLUS: "pro_plus",
            settings.PADDLE_PRICE_BUSINESS: "business",
            # Known default Fallback IDs
            "pri_01m2p85k69p7fxaa2aam45r4jw": "pro",
            "pri_01m2p89n5cce3wjzk8y1aerbg1": "pro_plus",
            "pri_01m2p8cbbevbzyvxgp5pfsg746": "business",
        }

    @classmethod
    def get_public_config(cls) -> Dict[str, Any]:
        """Returns safe, public client configuration for Paddle.js overlay checkout."""
        return {
            "environment": settings.PADDLE_ENVIRONMENT,
            "client_token": settings.PADDLE_CLIENT_TOKEN,
            "prices": {
                "pro": settings.PADDLE_PRICE_PRO,
                "pro_plus": settings.PADDLE_PRICE_PRO_PLUS,
                "business": settings.PADDLE_PRICE_BUSINESS,
            },
        }

    @classmethod
    def create_checkout_url(cls, user: User, plan_id: str) -> Dict[str, Any]:
        """Generates a secure hosted Paddle checkout URL with user metadata."""
        import urllib.parse
        plan_id = plan_id.lower().strip()
        price_map = {
            "pro": settings.PADDLE_PRICE_PRO,
            "pro_plus": settings.PADDLE_PRICE_PRO_PLUS,
            "business": settings.PADDLE_PRICE_BUSINESS,
        }
        price_id = price_map.get(plan_id)
        if not price_id:
            raise ValueError(f"Invalid plan '{plan_id}' requested.")

        base_host = "https://sandbox-buy.paddle.com" if settings.PADDLE_ENVIRONMENT == "sandbox" else "https://buy.paddle.com"
        
        custom_data_json = json.dumps({
            "userId": user.id,
            "userEmail": user.email,
            "userName": user.name or "",
            "planId": plan_id
        })
        
        query = urllib.parse.urlencode({
            "_price": price_id,
            "customer_email": user.email,
            "custom_data": custom_data_json,
        })
        checkout_url = f"{base_host}/checkout?{query}"
        
        return {
            "checkout_url": checkout_url,
            "price_id": price_id,
            "plan_id": plan_id,
            "environment": settings.PADDLE_ENVIRONMENT
        }

    @classmethod
    def verify_webhook_signature(
        cls, raw_body: bytes, signature_header: Optional[str]
    ) -> bool:
        """
        Verifies Paddle v2 webhook signature from Paddle-Signature header.
        Format: ts=1671552777;h1=04f58c7344df38c5d1052fbefec3...
        """
        secret = settings.PADDLE_WEBHOOK_SECRET_KEY
        if not secret:
            if settings.PADDLE_ENVIRONMENT == "sandbox":
                logger.warning(
                    "[Billing] PADDLE_WEBHOOK_SECRET_KEY not configured. Permitting webhook in sandbox mode."
                )
                return True
            logger.error("[Billing] Webhook signature verification failed: secret not configured.")
            return False

        if not signature_header:
            logger.error("[Billing] Webhook missing Paddle-Signature header.")
            return False

        try:
            parts = dict(item.split("=", 1) for item in signature_header.split(";") if "=" in item)
            ts = parts.get("ts")
            h1 = parts.get("h1")

            if not ts or not h1:
                logger.error("[Billing] Invalid Paddle-Signature header format.")
                return False

            signed_payload = f"{ts}:{raw_body.decode('utf-8')}"
            computed = hmac.new(
                secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            is_valid = hmac.compare_digest(computed, h1)
            if not is_valid:
                logger.warning("[Billing] Webhook signature HMAC mismatch.")
            return is_valid
        except Exception as e:
            logger.error(f"[Billing] Error during signature verification: {e}")
            return False

    @classmethod
    def process_webhook_event(
        cls, db: Session, raw_body: bytes, signature_header: Optional[str]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Parses and handles verified Paddle webhook events with idempotency.
        """
        if not cls.verify_webhook_signature(raw_body, signature_header):
            return False, "Invalid webhook signature", {"status": 401}

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except Exception as e:
            logger.error(f"[Billing] Failed to parse JSON webhook payload: {e}")
            return False, "Invalid JSON payload", {"status": 400}

        event_id = payload.get("event_id") or payload.get("data", {}).get("id")
        event_type = payload.get("event_type", "unknown")

        if not event_id:
            logger.error("[Billing] Webhook payload missing event_id.")
            return False, "Missing event_id", {"status": 400}

        # ── IDEMPOTENCY CHECK ──────────────────────────────────────────────
        existing_event = (
            db.query(PaddleWebhookEvent)
            .filter(PaddleWebhookEvent.event_id == event_id)
            .first()
        )
        if existing_event:
            logger.info(f"[Billing] Duplicate webhook event ignored: {event_id} ({event_type})")
            return True, "Duplicate event already processed", {"duplicate": True}

        # Record event for idempotency
        try:
            webhook_record = PaddleWebhookEvent(
                event_id=event_id,
                event_type=event_type,
                payload=raw_body.decode("utf-8"),
                processed_at=datetime.utcnow(),
            )
            db.add(webhook_record)
            db.commit()
        except Exception as db_err:
            db.rollback()
            logger.warning(f"[Billing] Could not save webhook event record: {db_err}")

        logger.info(f"[Billing] Webhook verified: event_type={event_type}, event_id={event_id}")

        data = payload.get("data", {})
        cls._handle_event(db, event_type, data)

        return True, "Webhook processed successfully", {"event_type": event_type}

    @classmethod
    def _find_user(cls, db: Session, data: Dict[str, Any]) -> Optional[User]:
        """Locates User entity using customData userId, subscription id, customer id, or email."""
        custom_data = data.get("custom_data") or {}
        user_id = custom_data.get("user_id") or custom_data.get("userId")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                return user

        subscription_id = data.get("id") if data.get("id", "").startswith("sub_") else data.get("subscription_id")
        if subscription_id:
            user = db.query(User).filter(User.paddle_subscription_id == subscription_id).first()
            if user:
                return user

        customer_id = data.get("customer_id")
        if customer_id:
            user = db.query(User).filter(User.paddle_customer_id == customer_id).first()
            if user:
                return user

        # Search by email if available in customer data
        customer_email = data.get("customer", {}).get("email") if isinstance(data.get("customer"), dict) else None
        if not customer_email and "user_email" in custom_data:
            customer_email = custom_data["user_email"]

        if customer_email:
            user = db.query(User).filter(User.email == customer_email).first()
            if user:
                return user

        return None

    @classmethod
    def _resolve_plan_from_items(cls, items: list) -> str:
        """Determines plan name from line items."""
        price_map = cls.get_price_plan_map()
        for item in items:
            price_id = item.get("price", {}).get("id") if isinstance(item.get("price"), dict) else item.get("price_id")
            if price_id and price_id in price_map:
                return price_map[price_id]
        return "free"

    @classmethod
    def _handle_event(cls, db: Session, event_type: str, data: Dict[str, Any]) -> None:
        """Dispatches logic for specific Paddle lifecycle events."""
        user = cls._find_user(db, data)
        if not user:
            logger.warning(f"[Billing] Could not find associated user for event {event_type}")
            return

        price_map = cls.get_price_plan_map()
        subscription_id = data.get("id") if data.get("id", "").startswith("sub_") else data.get("subscription_id")
        customer_id = data.get("customer_id")
        status = data.get("status", "active")
        next_billed_at_str = data.get("next_billed_at")
        management_urls = data.get("management_urls") or {}

        if customer_id:
            user.paddle_customer_id = customer_id
        if subscription_id:
            user.paddle_subscription_id = subscription_id

        if management_urls.get("cancel"):
            user.cancel_url = management_urls.get("cancel")
        if management_urls.get("update_payment_method"):
            user.update_url = management_urls.get("update_payment_method")

        # Parse next billing date if provided
        if next_billed_at_str:
            try:
                # Paddle provides ISO 8601 like 2026-09-17T02:00:00.000Z
                clean_date = next_billed_at_str.replace("Z", "+00:00")
                parsed_date = datetime.fromisoformat(clean_date)
                # Store as naive UTC in SQLite
                user.next_billing_date = parsed_date.replace(tzinfo=None)
                user.cycle_end_date = user.next_billing_date
            except Exception as e:
                logger.warning(f"[Billing] Failed parsing next_billed_at '{next_billed_at_str}': {e}")

        if event_type in ("subscription.created", "subscription.updated", "subscription.activated"):
            items = data.get("items", [])
            new_plan = cls._resolve_plan_from_items(items)

            user.subscription_status = status
            if status in ("active", "trialing") and new_plan != "free":
                user.plan = new_plan
                logger.info(f"[Billing] Plan synchronized: user={user.email}, plan={new_plan}, status={status}")
            elif status in ("past_due", "paused"):
                user.subscription_status = status
                logger.info(f"[Billing] Subscription status updated: user={user.email}, status={status}")

            db.commit()
            db.refresh(user)

        elif event_type in ("subscription.canceled", "subscription.past_due", "subscription.paused"):
            user.subscription_status = status
            # If immediately canceled without remaining cycle, revert to free
            if status == "canceled":
                now = datetime.utcnow()
                if not user.cycle_end_date or now >= user.cycle_end_date:
                    user.plan = "free"
            logger.info(f"[Billing] Subscription {event_type}: user={user.email}, status={status}")
            db.commit()
            db.refresh(user)

        elif event_type in ("transaction.paid", "transaction.completed"):
            details = data.get("details", {})
            line_items = details.get("line_items", []) or data.get("items", [])
            new_plan = cls._resolve_plan_from_items(line_items)

            if new_plan != "free":
                user.plan = new_plan
                user.subscription_status = "active"
                logger.info(f"[Billing] Transaction confirmed: user={user.email}, upgraded to {new_plan}")
            db.commit()
            db.refresh(user)

        elif event_type == "transaction.payment_failed":
            logger.warning(f"[Billing] Transaction payment failed for user={user.email}")
            user.subscription_status = "past_due"
            db.commit()
            db.refresh(user)
