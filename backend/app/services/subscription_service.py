import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.models.user import User
from backend.app.db.session import SessionLocal

PLAN_PRICING: Dict[str, float] = {
    "free": 0.0,
    "pro": 10.0,
    "pro_plus": 25.0,
    "business": 75.0
}

PLAN_LIMITS: Dict[str, int] = {
    "free": 15,
    "pro": 50,
    "pro_plus": 150,
    "business": 500
}

PLAN_DISPLAY_NAMES: Dict[str, str] = {
    "free": "Free",
    "pro": "Pro",
    "pro_plus": "Pro Plus",
    "business": "Business"
}

class SubscriptionService:
    @staticmethod
    def get_plan_details() -> Dict[str, Dict[str, Any]]:
        """Returns details of all subscription plans."""
        return {
            "free": {
                "id": "free",
                "name": "Free",
                "price": 0,
                "price_currency": "USD",
                "requests_limit": 15,
                "description": "Essential CAD engineering for hobbyists and initial evaluations.",
                "features": [
                    "15 total generation requests (2D DXF + 3D STL combined)",
                    "Standard 3D mesh & DXF generation",
                    "Community support",
                    "30-day rolling cycle"
                ]
            },
            "pro": {
                "id": "pro",
                "name": "Pro",
                "price": 10,
                "price_currency": "USD",
                "requests_limit": 50,
                "description": "Ideal for individual CNC machinists and precision designers.",
                "features": [
                    "50 total generation requests (2D + 3D combined)",
                    "High-resolution 3D CAD modeling",
                    "Parametric DXF generation & editing",
                    "Priority generation queue",
                    "30-day rolling cycle"
                ]
            },
            "pro_plus": {
                "id": "pro_plus",
                "name": "Pro Plus",
                "price": 25,
                "price_currency": "USD",
                "requests_limit": 150,
                "description": "Advanced capacity for active prototyping workshops & design studios.",
                "features": [
                    "150 total generation requests (2D + 3D combined)",
                    "Industrial-grade geometric tolerances",
                    "Multi-version revision history",
                    "Priority server processing",
                    "30-day rolling cycle"
                ]
            },
            "business": {
                "id": "business",
                "name": "Business",
                "price": 75,
                "price_currency": "USD",
                "requests_limit": 500,
                "description": "Maximum throughput for production manufacturing facilities.",
                "features": [
                    "500 total generation requests (2D + 3D combined)",
                    "Dedicated compute prioritization",
                    "Automated nesting & validation tools",
                    "Priority technical support",
                    "30-day rolling cycle"
                ]
            }
        }

    @staticmethod
    def get_or_init_user(db: Session, user_id: str) -> Optional[User]:
        """Finds user or auto-initializes new user record on default Free plan."""
        if not user_id:
            user_id = "default_user"
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            now = datetime.utcnow()
            user = User(
                id=user_id,
                name="CAD Engineer",
                email=f"{user_id}@example.com" if "@" not in user_id else user_id,
                password_hash="placeholder_demo_hash",
                is_email_verified=True,
                is_active=True,
                plan="free",
                requests_used_current_cycle=0,
                cycle_start_date=now,
                cycle_end_date=now + timedelta(days=30),
                is_admin=False
            )

            db.add(user)
            db.commit()
            db.refresh(user)
        return user


    @staticmethod
    def refresh_user_cycle_if_expired(db: Session, user: User) -> bool:
        """
        Checks if current rolling billing cycle has ended.
        If now > cycle_end_date, resets requests counter to 0 and extends cycle dates by 30 days.
        Returns True if cycle was refreshed, False otherwise.
        """
        now = datetime.utcnow()
        if not user.cycle_end_date or now > user.cycle_end_date:
            user.requests_used_current_cycle = 0
            user.cycle_start_date = now
            user.cycle_end_date = now + timedelta(days=30)
            db.commit()
            db.refresh(user)
            return True
        return False

    @classmethod
    def check_and_increment_usage(cls, db: Session, user_id: str) -> Tuple[bool, int, int, str]:
        """
        Backend security enforcement on generation endpoints.
        1. Refreshes rolling cycle if expired.
        2. Validates requests_used_current_cycle < plan limit.
        3. Increments usage and commits immediately to DB.
        
        Raises HTTP 429 if limit is reached.
        Returns (allowed, used_after_increment, limit, plan).
        """
        user = cls.get_or_init_user(db, user_id)
        if not user:
            # If user not found, raise 401
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated for generation request."
            )

        # 1. Rolling cycle check
        cls.refresh_user_cycle_if_expired(db, user)

        plan = (user.plan or "free").lower()
        limit = PLAN_LIMITS.get(plan, 15)
        current_used = user.requests_used_current_cycle or 0

        # 2. Limit enforcement
        if current_used >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "PLAN_LIMIT_REACHED",
                    "message": f"You've reached your monthly limit ({current_used}/{limit}). Upgrade your plan to continue.",
                    "used": current_used,
                    "limit": limit,
                    "plan": plan,
                    "cycle_end_date": user.cycle_end_date.isoformat() if user.cycle_end_date else None,
                    "upgrade_url": "/settings"
                }
            )

        # 3. Increment and save
        user.requests_used_current_cycle = current_used + 1
        db.commit()
        db.refresh(user)

        return (True, user.requests_used_current_cycle, limit, plan)

    @classmethod
    def get_subscription_status(cls, db: Session, user_id: str) -> Dict[str, Any]:
        """Retrieves full subscription and billing status for a user."""
        user = cls.get_or_init_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check and update rolling cycle
        cls.refresh_user_cycle_if_expired(db, user)

        plan = (user.plan or "free").lower()
        limit = PLAN_LIMITS.get(plan, 15)
        used = user.requests_used_current_cycle or 0
        remaining = max(0, limit - used)

        return {
            "user_id": user.id,
            "plan": plan,
            "plan_display_name": PLAN_DISPLAY_NAMES.get(plan, plan.title()),
            "requests_used": used,
            "requests_limit": limit,
            "requests_remaining": remaining,
            "cycle_start_date": user.cycle_start_date.isoformat() if user.cycle_start_date else None,
            "cycle_end_date": user.cycle_end_date.isoformat() if user.cycle_end_date else None,
            "is_admin": bool(user.is_admin),
            "plans_catalog": cls.get_plan_details(),
            "paddle_customer_id": user.paddle_customer_id,
            "paddle_subscription_id": user.paddle_subscription_id,
            "subscription_status": user.subscription_status or "active",
            "next_billing_date": user.next_billing_date.isoformat() if user.next_billing_date else (user.cycle_end_date.isoformat() if user.cycle_end_date else None),
            "cancel_url": user.cancel_url,
            "update_url": user.update_url,
        }
