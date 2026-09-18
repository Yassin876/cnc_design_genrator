#!/usr/bin/env python3
"""
CNC Design Generator — End-to-End API Test Suite
Tests real REQUEST → BACKEND → DATABASE → RESPONSE flows against live services.
Run: python scripts/e2e_api_test.py
Requires: httpx (pip install httpx)
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORAGE_UPLOADS = PROJECT_ROOT / "storage" / "uploads"
STORAGE_OUTPUTS = PROJECT_ROOT / "storage" / "outputs"
STORAGE_TEMP = PROJECT_ROOT / "storage" / "temp"

BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
AI_2D_URL = os.getenv("TEST_AI_2D_URL", "http://127.0.0.1:8001")
EDIT_URL = os.getenv("TEST_EDIT_URL", "http://127.0.0.1:8002")
NESTING_URL = os.getenv("TEST_NESTING_URL", "http://127.0.0.1:8003")
API = f"{BASE_URL}/api/v1"

MINIMAL_DXF = """0
SECTION
2
ENTITIES
0
LINE
8
OUTLINE
10
0.0
20
0.0
30
0.0
11
100.0
21
100.0
31
0.0
0
CIRCLE
8
HOLES
10
50.0
20
50.0
30
0.0
40
10.0
0
ENDSEC
0
EOF
"""

MINIMAL_STL = """solid test_cube
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 100 0 0
      vertex 100 100 0
    endloop
  endfacet
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 100 100 0
      vertex 0 100 0
    endloop
  endfacet
endsolid test_cube
"""


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    skipped: bool = False


@dataclass
class TestContext:
    client: httpx.Client
    email: str = ""
    password: str = "Test1234!"
    name: str = "E2E Tester"
    access_token: str = ""
    refresh_token: str = ""
    user_id: str = ""
    project_id: str = ""
    uploaded_path: str = ""
    dxf_path: str = ""
    stl_path: str = ""
    user_b_token: str = ""
    results: list[TestResult] = field(default_factory=list)


def record(ctx: TestContext, name: str, passed: bool, detail: str = "", skipped: bool = False) -> None:
    status = "SKIP" if skipped else ("PASS" if passed else "FAIL")
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    ctx.results.append(TestResult(name=name, passed=passed, detail=detail, skipped=skipped))


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def wait_for_service(url: str, label: str, timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    print(f"  [WARN] {label} not reachable at {url}")
    return False


# ── Phase 0: Service health ──────────────────────────────────────────────────

def test_service_health(ctx: TestContext) -> None:
    print("\n=== Phase 0: Service Health ===")
    checks = [
        ("main_backend", f"{BASE_URL}/api/v1/health"),
        ("ai_server_2d", f"{AI_2D_URL}/health"),
        ("edit_server", f"{EDIT_URL}/health"),
        ("nesting_worker", f"{NESTING_URL}/health"),
    ]
    for name, url in checks:
        ok = wait_for_service(url, name, timeout=5.0)
        record(ctx, f"health/{name}", ok, url if ok else f"unreachable: {url}")


# ── Phase 1: Auth ──────────────────────────────────────────────────────────────

def test_auth(ctx: TestContext) -> None:
    print("\n=== Phase 1: Auth ===")
    suffix = uuid.uuid4().hex[:8]
    ctx.email = f"e2e_{suffix}@test.com"

    # register-dev (auto-verify for testing)
    r = ctx.client.post(f"{API}/auth/register-dev", json={
        "name": ctx.name,
        "email": ctx.email,
        "password": ctx.password,
        "confirm_password": ctx.password,
    })
    ok = r.status_code == 200 and "access_token" in r.json()
    record(ctx, "auth/register-dev", ok, f"status={r.status_code}")
    if not ok:
        return

    data = r.json()
    ctx.access_token = data["access_token"]
    ctx.refresh_token = data.get("refresh_token", "")
    ctx.user_id = data.get("user", {}).get("id", "")

    # login
    r = ctx.client.post(f"{API}/auth/login", json={"email": ctx.email, "password": ctx.password})
    ok = r.status_code == 200 and "access_token" in r.json()
    record(ctx, "auth/login", ok, f"status={r.status_code}")
    if ok:
        ctx.access_token = r.json()["access_token"]
        ctx.refresh_token = r.json().get("refresh_token", ctx.refresh_token)

    # me
    r = ctx.client.get(f"{API}/auth/me", headers=auth_headers(ctx.access_token))
    body = r.json()
    ok = r.status_code == 200 and body.get("email") == ctx.email and "password" not in body
    record(ctx, "auth/me", ok, f"email={body.get('email')}")

    # refresh
    if ctx.refresh_token:
        r = ctx.client.post(f"{API}/auth/refresh", json={"refresh_token": ctx.refresh_token})
        ok = r.status_code == 200 and "access_token" in r.json()
        new_token = r.json().get("access_token", "") if ok else ""
        record(ctx, "auth/refresh", ok and bool(new_token), "new token issued" if ok else r.text[:120])
        if ok:
            ctx.access_token = new_token


# ── Phase 2: Projects ────────────────────────────────────────────────────────

def test_projects(ctx: TestContext) -> None:
    print("\n=== Phase 2: Projects ===")
    if not ctx.access_token:
        record(ctx, "projects/*", False, "no auth token")
        return

    h = auth_headers(ctx.access_token)

    r = ctx.client.post(f"{API}/projects", headers=h, json={
        "name": "E2E Test Project",
        "description": "Automated test project",
        "type": "2D",
    })
    ok = r.status_code == 201
    body = r.json() if ok else {}
    ctx.project_id = body.get("id", "")
    record(ctx, "projects/create", ok and bool(ctx.project_id), f"id={ctx.project_id}")

    r = ctx.client.get(f"{API}/projects", headers=h)
    projects = r.json() if r.status_code == 200 else []
    ok = r.status_code == 200 and any(p.get("id") == ctx.project_id for p in projects)
    record(ctx, "projects/list", ok, f"count={len(projects)}")

    r = ctx.client.patch(f"{API}/projects/{ctx.project_id}", headers=h, json={
        "name": "E2E Updated Project",
        "description": "Updated by test",
    })
    ok = r.status_code == 200 and r.json().get("name") == "E2E Updated Project"
    record(ctx, "projects/update", ok)

    r = ctx.client.delete(f"{API}/projects/{ctx.project_id}", headers=h)
    ok = r.status_code == 200
    record(ctx, "projects/delete-to-trash", ok, r.json().get("message", ""))

    r = ctx.client.get(f"{API}/projects/trash", headers=h)
    trash = r.json() if r.status_code == 200 else []
    in_trash = any(p.get("id") == ctx.project_id for p in trash)
    record(ctx, "projects/in-trash", in_trash)

    r = ctx.client.post(f"{API}/projects/{ctx.project_id}/restore", headers=h)
    record(ctx, "projects/restore", r.status_code == 200)


# ── Phase 3: Files ─────────────────────────────────────────────────────────────

def test_files(ctx: TestContext) -> None:
    print("\n=== Phase 3: Files ===")
    if not ctx.access_token:
        record(ctx, "files/*", False, "no auth token")
        return

    h = auth_headers(ctx.access_token)
    STORAGE_UPLOADS.mkdir(parents=True, exist_ok=True)
    STORAGE_TEMP.mkdir(parents=True, exist_ok=True)

    dxf_local = STORAGE_TEMP / f"e2e_sample_{uuid.uuid4().hex[:6]}.dxf"
    dxf_local.write_text(MINIMAL_DXF, encoding="utf-8")
    ctx.dxf_path = str(dxf_local)

    with open(dxf_local, "rb") as f:
        r = ctx.client.post(f"{API}/files/upload", headers=h, files={"file": ("sample.dxf", f, "application/octet-stream")})
    ok = r.status_code == 200 and r.json().get("status") == "SUCCESS"
    ctx.uploaded_path = r.json().get("saved_path", "") if ok else ""
    record(ctx, "files/upload-dxf", ok, ctx.uploaded_path)

    if ctx.uploaded_path:
        r = ctx.client.get(f"{API}/files/download", headers=h, params={"file_path": ctx.uploaded_path})
        ok = r.status_code == 200 and len(r.content) > 0
        record(ctx, "files/download-dxf", ok, f"bytes={len(r.content) if ok else 0}")


# ── Phase 4: CAD ───────────────────────────────────────────────────────────────

def test_cad(ctx: TestContext) -> None:
    print("\n=== Phase 4: CAD ===")
    if not ctx.access_token:
        record(ctx, "cad/*", False, "no auth token")
        return

    h = auth_headers(ctx.access_token)
    path = ctx.uploaded_path or ctx.dxf_path
    if not path:
        record(ctx, "cad/parse-dxf", False, "no dxf path")
        return

    r = ctx.client.post(f"{API}/cad/parse-dxf", headers=h, json={"file_path": path})
    ok = r.status_code == 200 and r.json().get("status") == "SUCCESS"
    entities = r.json().get("entities", []) if ok else []
    record(ctx, "cad/parse-dxf", ok, f"entities={len(entities) if isinstance(entities, list) else 'object'}")

    STORAGE_OUTPUTS.mkdir(parents=True, exist_ok=True)
    stl_local = STORAGE_TEMP / f"e2e_cube_{uuid.uuid4().hex[:6]}.stl"
    stl_local.write_text(MINIMAL_STL, encoding="utf-8")
    ctx.stl_path = str(stl_local)

    r = ctx.client.get(f"{API}/cad/inspect-3d", headers=h, params={"file_path": ctx.stl_path})
    ok = r.status_code == 200
    record(ctx, "cad/inspect-3d", ok, f"status={r.status_code}" if not ok else "mesh inspected")

    if ctx.uploaded_path:
        r = ctx.client.post(f"{API}/cad/nesting", headers=h, json={
            "part_paths": [ctx.uploaded_path],
            "sheet_width": 500,
            "sheet_height": 300,
            "spacing": 5,
            "allow_rotate": True,
        })
        ok = r.status_code == 200
        record(ctx, "cad/nesting", ok, f"status={r.status_code}" + ("" if ok else f" {r.text[:100]}"))


# ── Phase 5: Billing ───────────────────────────────────────────────────────────

def test_billing(ctx: TestContext) -> None:
    print("\n=== Phase 5: Billing ===")
    if not ctx.access_token:
        record(ctx, "billing/*", False, "no auth token")
        return

    h = auth_headers(ctx.access_token)

    r = ctx.client.get(f"{API}/billing/config")
    record(ctx, "billing/config", r.status_code == 200)

    r = ctx.client.get(f"{API}/billing/status", headers=h)
    ok = r.status_code == 200 and "plan" in r.json()
    record(ctx, "billing/status", ok)

    r = ctx.client.post(f"{API}/billing/payment/mock-checkout", headers=h, json={"plan_requested": "pro"})
    ok = r.status_code == 200 and r.json().get("success") is True
    record(ctx, "billing/mock-checkout", ok, r.json().get("message", "")[:80] if ok else r.text[:120])

    if ok:
        r = ctx.client.get(f"{API}/billing/status", headers=h)
        plan = r.json().get("plan") if r.status_code == 200 else ""
        record(ctx, "billing/plan-upgraded", plan == "pro", f"plan={plan}")


# ── Phase 6: User isolation ────────────────────────────────────────────────────

def test_user_isolation(ctx: TestContext) -> None:
    print("\n=== Phase 6: User Isolation ===")
    if not ctx.access_token or not ctx.project_id:
        record(ctx, "isolation/*", False, "missing user A context", skipped=True)
        return

    suffix = uuid.uuid4().hex[:8]
    email_b = f"e2e_b_{suffix}@test.com"
    r = ctx.client.post(f"{API}/auth/register-dev", json={
        "name": "User B",
        "email": email_b,
        "password": ctx.password,
        "confirm_password": ctx.password,
    })
    if r.status_code != 200:
        record(ctx, "isolation/register-user-b", False, r.text[:120])
        return

    ctx.user_b_token = r.json()["access_token"]
    record(ctx, "isolation/register-user-b", True)

    r = ctx.client.get(f"{API}/projects/{ctx.project_id}", headers=auth_headers(ctx.user_b_token))
    record(ctx, "isolation/cannot-read-other-project", r.status_code in (403, 404), f"status={r.status_code}")


# ── Phase 7: Generation (optional — needs AI keys) ────────────────────────────

def test_generation(ctx: TestContext) -> None:
    print("\n=== Phase 7: Generation (optional) ===")
    if not ctx.access_token or not ctx.project_id:
        record(ctx, "generation/*", False, "no context", skipped=True)
        return

    if not os.getenv("GEMINI_API_KEY") and not os.getenv("HF_TOKEN"):
        record(ctx, "generation/text-to-3d", True, "skipped — no AI keys configured", skipped=True)
        return

    h = auth_headers(ctx.access_token)
    r = ctx.client.post(f"{API}/generation/text-to-3d", headers=h, json={
        "prompt": "simple box 50x50x30mm",
        "project_id": ctx.project_id,
        "height": 30,
        "width": 50,
        "length": 50,
    }, timeout=120.0)
    ok = r.status_code == 200 and r.json().get("status") in ("completed", "processing")
    record(ctx, "generation/text-to-3d", ok, f"status={r.status_code}")


# ── Phase 8: Database persistence hint ────────────────────────────────────────

def test_db_file_exists(ctx: TestContext) -> None:
    print("\n=== Phase 8: Database ===")
    db_path = PROJECT_ROOT / "cad_studio.db"
    record(ctx, "database/file-exists", db_path.exists(), str(db_path))


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_all() -> int:
    print("=" * 60)
    print("CNC Design Generator — E2E API Test Suite")
    print("=" * 60)

    ctx = TestContext(client=httpx.Client(timeout=60.0))

    test_service_health(ctx)
    if not any(r.passed for r in ctx.results if r.name.startswith("health/main_backend")):
        print("\n[FATAL] Main backend (8000) is not running. Start with:")
        print("  python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000")
        return 1

    test_auth(ctx)
    test_projects(ctx)
    test_files(ctx)
    test_cad(ctx)
    test_billing(ctx)
    test_user_isolation(ctx)
    test_generation(ctx)
    test_db_file_exists(ctx)

    passed = sum(1 for r in ctx.results if r.passed and not r.skipped)
    failed = sum(1 for r in ctx.results if not r.passed and not r.skipped)
    skipped = sum(1 for r in ctx.results if r.skipped)

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed, {skipped} skipped / {len(ctx.results)} total")
    print("=" * 60)

    if failed:
        print("\nFailed tests:")
        for r in ctx.results:
            if not r.passed and not r.skipped:
                print(f"  - {r.name}: {r.detail}")

    status = "FULLY TESTED" if failed == 0 else "PARTIALLY TESTED"
    print(f"\nStatus: {status}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())
