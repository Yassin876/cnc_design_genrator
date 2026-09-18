import sys
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_db, init_db
from backend.app.models.user import User
from backend.app.models.paddle_event import PaddleWebhookEvent
from backend.app.services.paddle_service import PaddleService

client = TestClient(app)

TEST_SECRET = "pdl_ntfset_test_secret_key_123"


def create_signed_headers(raw_body: bytes, secret: str = TEST_SECRET) -> dict:
    ts = str(int(datetime.utcnow().timestamp()))
    signed_payload = f"{ts}:{raw_body.decode('utf-8')}"
    h1 = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "Content-Type": "application/json",
        "Paddle-Signature": f"ts={ts};h1={h1}"
    }


def test_paddle_public_config():
    """Verify that public paddle config returns environment, token, and price IDs."""
    response = client.get("/api/v1/billing/paddle/config")
    assert response.status_code == 200
    data = response.json()
    assert "environment" in data
    assert "client_token" in data
    assert "prices" in data
    assert data["prices"]["pro"] == "pri_01m2p85k69p7fxaa2aam45r4jw"
    assert data["prices"]["pro_plus"] == "pri_01m2p89n5cce3wjzk8y1aerbg1"
    assert data["prices"]["business"] == "pri_01m2p8cbbevbzyvxgp5pfsg746"


def test_create_paddle_checkout_session():
    """Verify that backend generates valid hosted checkout URLs for Pro, Pro Plus, and Business."""
    from backend.app.core.security import create_access_token
    init_db()
    db_gen = get_db()
    db = next(db_gen)

    test_user_id = "test_checkout_user_1"
    existing = db.query(User).filter(User.id == test_user_id).first()
    if existing:
        db.delete(existing)
        db.commit()

    test_user = User(
        id=test_user_id,
        name="Checkout Tester",
        email="checkout_tester@antidesign.ai",
        plan="free",
        requests_used_current_cycle=0,
        cycle_start_date=datetime.utcnow(),
        cycle_end_date=datetime.utcnow() + timedelta(days=30),
    )
    db.add(test_user)
    db.commit()

    try:
        token = create_access_token(test_user_id, email="checkout_tester@antidesign.ai")

        # Pro
        res_pro = client.post(
            "/api/v1/billing/paddle/create-checkout",
            json={"plan_id": "pro"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_pro.status_code == 200
        data_pro = res_pro.json()
        assert "checkout_url" in data_pro
        assert data_pro["price_id"] == "pri_01m2p85k69p7fxaa2aam45r4jw"

        # Pro Plus
        res_plus = client.post(
            "/api/v1/billing/paddle/create-checkout",
            json={"plan_id": "pro_plus"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_plus.status_code == 200
        data_plus = res_plus.json()
        assert data_plus["price_id"] == "pri_01m2p89n5cce3wjzk8y1aerbg1"

        # Business
        res_biz = client.post(
            "/api/v1/billing/paddle/create-checkout",
            json={"plan_id": "business"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_biz.status_code == 200
        data_biz = res_biz.json()
        assert data_biz["price_id"] == "pri_01m2p8cbbevbzyvxgp5pfsg746"
    finally:
        db.delete(test_user)
        db.commit()


def test_paddle_webhook_flow_and_idempotency():
    """Test full webhook lifecycle with idempotency and user plan synchronization."""
    import uuid
    init_db()

    orig_secret = settings.PADDLE_WEBHOOK_SECRET_KEY
    settings.PADDLE_WEBHOOK_SECRET_KEY = TEST_SECRET

    try:
        run_id = uuid.uuid4().hex[:6]

        # Create a test user in database
        db_gen = get_db()
        db = next(db_gen)

        test_user_id = f"test_paddle_user_{run_id}"
        existing = db.query(User).filter(User.id == test_user_id).first()
        if existing:
            db.delete(existing)
            db.commit()

        test_user = User(
            id=test_user_id,
            name="Paddle Tester",
            email=f"paddletest_{run_id}@antidesign.ai",
            plan="free",
            requests_used_current_cycle=0,
            cycle_start_date=datetime.utcnow(),
            cycle_end_date=datetime.utcnow() + timedelta(days=30),
        )
        db.add(test_user)
        db.commit()

        # 1. Simulate subscription.created webhook for Pro plan
        webhook_payload = {
            "event_id": f"evt_test_01m2p8_pro_{run_id}",
            "event_type": "subscription.created",
            "data": {
                "id": f"sub_test_{run_id}",
                "customer_id": f"ctm_test_{run_id}",
                "status": "active",
                "next_billed_at": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
                "items": [
                    {
                        "price_id": "pri_01m2p85k69p7fxaa2aam45r4jw",
                        "quantity": 1
                    }
                ],
                "custom_data": {
                    "user_id": test_user_id,
                    "user_email": f"paddletest_{run_id}@antidesign.ai"
                },
                "management_urls": {
                    "cancel": f"https://buy.paddle.com/subscription/cancel/sub_test_{run_id}",
                    "update_payment_method": f"https://buy.paddle.com/subscription/update/sub_test_{run_id}"
                }
            }
        }

        raw_body = json.dumps(webhook_payload).encode("utf-8")
        headers = create_signed_headers(raw_body)
        response = client.post(
            "/api/v1/billing/paddle/webhook",
            content=raw_body,
            headers=headers
        )
        assert response.status_code == 200
        res_data = response.json()
        assert res_data["success"] is True

        # Verify user was upgraded to Pro in database
        db.refresh(test_user)
        assert test_user.plan == "pro"
        assert test_user.paddle_subscription_id == f"sub_test_{run_id}"
        assert test_user.paddle_customer_id == f"ctm_test_{run_id}"
        assert test_user.subscription_status == "active"
        assert test_user.cancel_url == f"https://buy.paddle.com/subscription/cancel/sub_test_{run_id}"

        # 2. Test Idempotency: replay the exact same webhook
        repeat_response = client.post(
            "/api/v1/billing/paddle/webhook",
            content=raw_body,
            headers=headers
        )
        assert repeat_response.status_code == 200
        repeat_data = repeat_response.json()
        assert repeat_data["details"].get("duplicate") is True

        # 3. Simulate upgrade to Pro Plus via subscription.updated
        update_payload = {
            "event_id": f"evt_test_01m2p8_proplus_{run_id}",
            "event_type": "subscription.updated",
            "data": {
                "id": f"sub_test_{run_id}",
                "customer_id": f"ctm_test_{run_id}",
                "status": "active",
                "next_billed_at": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
                "items": [
                    {
                        "price_id": "pri_01m2p89n5cce3wjzk8y1aerbg1",
                        "quantity": 1
                    }
                ],
                "custom_data": {
                    "user_id": test_user_id
                }
            }
        }
        raw_update_body = json.dumps(update_payload).encode("utf-8")
        update_headers = create_signed_headers(raw_update_body)
        update_response = client.post(
            "/api/v1/billing/paddle/webhook",
            content=raw_update_body,
            headers=update_headers
        )
        assert update_response.status_code == 200
        db.refresh(test_user)
        assert test_user.plan == "pro_plus"

        # 4. Simulate cancellation via subscription.canceled
        cancel_payload = {
            "event_id": f"evt_test_01m2p8_canceled_{run_id}",
            "event_type": "subscription.canceled",
            "data": {
                "id": f"sub_test_{run_id}",
                "customer_id": f"ctm_test_{run_id}",
                "status": "canceled",
                "custom_data": {
                    "user_id": test_user_id
                }
            }
        }
        raw_cancel_body = json.dumps(cancel_payload).encode("utf-8")
        cancel_headers = create_signed_headers(raw_cancel_body)
        cancel_response = client.post(
            "/api/v1/billing/paddle/webhook",
            content=raw_cancel_body,
            headers=cancel_headers
        )
        assert cancel_response.status_code == 200
        db.refresh(test_user)
        assert test_user.subscription_status == "canceled"

        # 5. Simulate transaction.payment_failed
        fail_payload = {
            "event_id": f"evt_test_01m2p8_tx_failed_{run_id}",
            "event_type": "transaction.payment_failed",
            "data": {
                "id": f"txn_test_failed_{run_id}",
                "customer_id": f"ctm_test_{run_id}",
                "custom_data": {
                    "user_id": test_user_id
                }
            }
        }
        raw_fail_body = json.dumps(fail_payload).encode("utf-8")
        fail_headers = create_signed_headers(raw_fail_body)
        fail_response = client.post(
            "/api/v1/billing/paddle/webhook",
            content=raw_fail_body,
            headers=fail_headers
        )
        assert fail_response.status_code == 200
        db.refresh(test_user)
        assert test_user.subscription_status == "past_due"

        # Clean up test user
        db.delete(test_user)
        db.commit()
    finally:
        settings.PADDLE_WEBHOOK_SECRET_KEY = orig_secret


def test_paddle_hmac_signature_verification():
    """Verify HMAC-SHA256 signature verification logic with a secret key."""
    secret = "pdl_ntfset_01testsecretkey123456789"
    original_secret = settings.PADDLE_WEBHOOK_SECRET_KEY
    settings.PADDLE_WEBHOOK_SECRET_KEY = secret

    try:
        test_payload = json.dumps({"event_id": "evt_sig_test_1", "event_type": "subscription.activated", "data": {}}).encode("utf-8")
        ts = "1726531200"
        signed_payload = f"{ts}:{test_payload.decode('utf-8')}"
        valid_h1 = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        valid_header = f"ts={ts};h1={valid_h1}"

        # 1. Valid Signature
        res = client.post(
            "/api/v1/billing/paddle/webhook",
            content=test_payload,
            headers={"Content-Type": "application/json", "Paddle-Signature": valid_header}
        )
        assert res.status_code == 200

        # 2. Tampered / Invalid Signature
        invalid_header = f"ts={ts};h1=invalid_signature_hash_value_here"
        bad_res = client.post(
            "/api/v1/billing/paddle/webhook",
            content=test_payload,
            headers={"Content-Type": "application/json", "Paddle-Signature": invalid_header}
        )
        assert bad_res.status_code == 401
    finally:
        settings.PADDLE_WEBHOOK_SECRET_KEY = original_secret


if __name__ == "__main__":
    test_paddle_public_config()
    test_create_paddle_checkout_session()
    test_paddle_webhook_flow_and_idempotency()
    test_paddle_hmac_signature_verification()
    print("ALL PADDLE BILLING TESTS PASSED SUCCESSFULLY!")
