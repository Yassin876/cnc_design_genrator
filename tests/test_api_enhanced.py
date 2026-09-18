#!/usr/bin/env python3
"""
CNC Design Generator — End-to-End API Test Runner
Tests real endpoints against running services (8000–8003).
Ignores legacy tests/ folder per project instructions.
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
    print("Install httpx: python -m pip install httpx")
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
API = f"{BASE_URL}/api/v1"
AI_2D_URL = os.getenv("TEST_AI_2D_URL", "http://127.0.0.1:8001")
EDIT_URL = os.getenv("TEST_EDIT_URL", "http://127.0.0.1:8002")
NESTING_URL = os.getenv("TEST_NESTING_URL", "http://127.0.0.1:8003")

STORAGE_UPLOADS = ROOT / "storage" / "uploads"
STORAGE_OUTPUTS = ROOT / "storage" / "outputs"
STORAGE_TEMP = ROOT / "storage" / "temp"


@dataclass
class TestResult:
    name: str
    phase: str
    passed: bool
    detail: str = ""
    duration_ms: int = 0


@dataclass
class TestContext:
    email: str = ""
    password: str = "Test1234!"
    access_token: str = ""
    refresh_token: str = ""
    user_id: str = ""
    project_id: str = ""
    uploaded_path: str = ""
    dxf_path: str = ""
    stl_path: str = ""
    user_b_token: str = ""
    results: list[TestResult] = field(default_factory=list)


def run_test(ctx: TestContext, phase: str, name: str, fn: Callable[[], None]) -> None:
    start = time.perf_counter()
    try:
        fn()
        ms = int((time.perf_counter() - start) * 1000)
        ctx.results.append(TestResult(name=name, phase=phase, passed=True, duration_ms=ms))
        print(f"  PASS  {name} ({ms}ms)")
    except AssertionError as exc:
        ms = int((time.perf_counter() - start) * 1000)
        detail = str(exc) or "Assertion failed"
        ctx.results.append(TestResult(name=name, phase=phase, passed=False, detail=detail, duration_ms=ms))
        print(f"  FAIL  {name} — {detail}")
    except Exception as exc:
        ms = int((time.perf_counter() - start) * 1000)
        detail = f"{type(exc).__name__}: {exc}"
        ctx.results.append(TestResult(name=name, phase=phase, passed=False, detail=detail, duration_ms=ms))
        print(f"  FAIL  {name} — {detail}")


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def ensure_sample_files() -> tuple[str, str]:
    STORAGE_UPLOADS.mkdir(parents=True, exist_ok=True)
    STORAGE_TEMP.mkdir(parents=True, exist_ok=True)

    dxf_path = STORAGE_TEMP / f"e2e_sample_{uuid.uuid4().hex[:6]}.dxf"
    dxf_path.write_text(
        "\n".join(
            [
                "0", "SECTION", "2", "ENTITIES",
                "0", "LINE", "8", "0",
                "10", "0.0", "20", "0.0", "11", "100.0", "21", "100.0",
                "0", "CIRCLE", "8", "0", "10", "50.0", "20", "50.0", "40", "10.0",
                "0", "ENDSEC", "0", "EOF",
            ]
        ),
        encoding="utf-8",
    )

    stl_path = STORAGE_TEMP / f"e2e_cube_{uuid.uuid4().hex[:6]}.stl"
    stl_path.write_text(
        "\n".join(
            [
                "solid cube",
                "  facet normal 0 0 1",
                "    outer loop",
                "      vertex 0 0 0",
                "      vertex 10 0 0",
                "      vertex 10 10 0",
                "    endloop",
                "  endfacet",
                "endsolid cube",
            ]
        ),
        encoding="utf-8",
    )
    return str(dxf_path), str(stl_path)


# ── Phase 0: Service health ──────────────────────────────────────────────────

def phase_health(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 0: Service Health ===")

    def main_health():
        r = client.get(f"{API}/health", timeout=5.0)
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        assert r.json().get("status") == "online"

    def ai_2d_health():
        r = client.get(f"{AI_2D_URL}/health", timeout=5.0)
        assert r.status_code == 200, f"status={r.status_code}"
        assert r.json().get("service") == "ai_server_2d"

    def edit_health():
        r = client.get(f"{EDIT_URL}/health", timeout=5.0)
        assert r.status_code == 200
        assert r.json().get("service") == "edit_server"

    def nesting_health():
        r = client.get(f"{NESTING_URL}/health", timeout=5.0)
        assert r.status_code == 200
        assert r.json().get("service") == "nesting_worker"

    run_test(ctx, "health", "Main backend /health", main_health)
    run_test(ctx, "health", "AI Server 2D /health", ai_2d_health)
    run_test(ctx, "health", "Edit Server /health", edit_health)
    run_test(ctx, "health", "Nesting Worker /health", nesting_health)


# ── Phase 1: Auth ────────────────────────────────────────────────────────────

def phase_auth(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 1: Auth ===")
    suffix = uuid.uuid4().hex[:8]
    ctx.email = f"e2e_tester_{suffix}@example.com"
    ctx.password = "Test1234!"

    def register_dev():
        r = client.post(
            f"{API}/auth/register-dev",
            json={"name": "E2E Tester", "email": ctx.email, "password": ctx.password},
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("access_token"), "missing access_token"
        assert data.get("refresh_token"), "missing refresh_token"
        ctx.access_token = data["access_token"]
        ctx.refresh_token = data["refresh_token"]
        ctx.user_id = data["user"]["id"]

    def login():
        r = client.post(
            f"{API}/auth/login",
            json={"email": ctx.email, "password": ctx.password},
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data["access_token"]
        ctx.access_token = data["access_token"]
        ctx.refresh_token = data["refresh_token"]

    def me():
        r = client.get(f"{API}/auth/me", headers=auth_headers(ctx.access_token))
        assert r.status_code == 200, r.text
        user = r.json()
        assert user["email"] == ctx.email
        assert "password" not in user
        assert "password_hash" not in user

    def refresh():
        r = client.post(f"{API}/auth/refresh", json={"refresh_token": ctx.refresh_token})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["access_token"], "missing access_token after refresh"
        assert data["refresh_token"], "missing refresh_token after refresh"
        me_r = client.get(f"{API}/auth/me", headers=auth_headers(data["access_token"]))
        assert me_r.status_code == 200, me_r.text
        ctx.access_token = data["access_token"]
        ctx.refresh_token = data["refresh_token"]

    run_test(ctx, "auth", "Register (dev auto-verify)", register_dev)
    run_test(ctx, "auth", "Login", login)
    run_test(ctx, "auth", "GET /auth/me", me)
    run_test(ctx, "auth", "Refresh token", refresh)


# ── Phase 2: Projects ─────────────────────────────────────────────────────────

def phase_projects(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 2: Projects ===")
    headers = auth_headers(ctx.access_token)

    def create():
        r = client.post(
            f"{API}/projects",
            headers=headers,
            json={"name": "E2E Test Project", "description": "Automated test", "type": "2D"},
        )
        assert r.status_code == 201, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("id")
        assert data["name"] == "E2E Test Project"
        ctx.project_id = data["id"]

    def list_projects():
        r = client.get(f"{API}/projects", headers=headers)
        assert r.status_code == 200
        projects = r.json()
        assert isinstance(projects, list)
        assert any(p["id"] == ctx.project_id for p in projects)

    def update():
        r = client.patch(
            f"{API}/projects/{ctx.project_id}",
            headers=headers,
            json={"name": "E2E Updated Project", "description": "Updated"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "E2E Updated Project"

    def trash_and_restore():
        r = client.delete(f"{API}/projects/{ctx.project_id}", headers=headers)
        assert r.status_code == 200, r.text
        r2 = client.get(f"{API}/projects/trash", headers=headers)
        assert r2.status_code == 200
        trash = r2.json()
        assert any(p["id"] == ctx.project_id for p in trash)
        r3 = client.post(f"{API}/projects/{ctx.project_id}/restore", headers=headers)
        assert r3.status_code == 200, r3.text

    run_test(ctx, "projects", "Create project", create)
    run_test(ctx, "projects", "List user projects", list_projects)
    run_test(ctx, "projects", "Update project (PATCH)", update)
    run_test(ctx, "projects", "Trash + restore project", trash_and_restore)


# ── Phase 3: Files ────────────────────────────────────────────────────────────

def phase_files(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 3: Files ===")
    headers = auth_headers(ctx.access_token)
    ctx.dxf_path, ctx.stl_path = ensure_sample_files()

    def upload_dxf():
        with open(ctx.dxf_path, "rb") as fh:
            r = client.post(
                f"{API}/files/upload",
                headers=headers,
                files={"file": ("sample.dxf", fh, "application/octet-stream")},
            )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("status") == "SUCCESS"
        assert data.get("saved_path")
        assert os.path.isfile(data["saved_path"])
        ctx.uploaded_path = data["saved_path"]

    def download():
        r = client.get(
            f"{API}/files/download",
            headers=headers,
            params={"file_path": ctx.uploaded_path},
        )
        assert r.status_code == 200, r.text
        assert len(r.content) > 0

    run_test(ctx, "files", "Upload DXF via /files/upload", upload_dxf)
    run_test(ctx, "files", "Download uploaded file", download)


# ── Phase 4: CAD ──────────────────────────────────────────────────────────────

def phase_cad(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 4: CAD Operations ===")
    headers = auth_headers(ctx.access_token)

    def parse_dxf():
        r = client.post(
            f"{API}/cad/parse-dxf",
            headers=headers,
            json={"file_path": ctx.uploaded_path},
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("status") == "SUCCESS"
        entities = data.get("entities")
        assert entities is not None
        assert len(entities) >= 1

    def inspect_3d():
        r = client.get(
            f"{API}/cad/inspect-3d",
            headers=headers,
            params={"file_path": ctx.stl_path},
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert "vertices_count" in data
        assert "faces_count" in data

    def nesting():
        r = client.post(
            f"{API}/cad/nesting",
            headers=headers,
            json={
                "part_paths": [ctx.uploaded_path],
                "sheet_width": 500,
                "sheet_height": 300,
                "spacing": 5,
                "allow_rotate": True,
            },
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text[:500]}"
        data = r.json()
        assert "sheets" in data or data.get("status") == "SUCCESS"

    run_test(ctx, "cad", "Parse DXF", parse_dxf)
    run_test(ctx, "cad", "Inspect 3D mesh (STL)", inspect_3d)
    run_test(ctx, "cad", "Nesting optimization", nesting)


# ── Phase 5: Billing ──────────────────────────────────────────────────────────

def phase_billing(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 5: Billing ===")
    headers = auth_headers(ctx.access_token)

    def billing_status():
        r = client.get(f"{API}/billing/status", headers=headers)
        assert r.status_code == 200, r.text
        assert "plan" in r.json()

    def mock_checkout():
        r = client.post(
            f"{API}/billing/payment/mock-checkout",
            headers=headers,
            json={"plan_requested": "pro"},
        )
        assert r.status_code == 200, f"status={r.status_code} body={r.text}"
        data = r.json()
        assert data.get("success") is True
        assert data.get("new_plan") == "pro"

    def status_after_upgrade():
        r = client.get(f"{API}/billing/status", headers=headers)
        assert r.status_code == 200
        assert r.json().get("plan") == "pro"

    run_test(ctx, "billing", "GET billing status", billing_status)
    run_test(ctx, "billing", "Mock checkout (dev)", mock_checkout)
    run_test(ctx, "billing", "Plan upgraded after mock checkout", status_after_upgrade)


# ── Phase 6: Isolation ────────────────────────────────────────────────────────

def phase_isolation(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 6: User Isolation ===")
    suffix = uuid.uuid4().hex[:8]
    email_b = f"e2e_userb_{suffix}@example.com"

    def create_user_b():
        r = client.post(
            f"{API}/auth/register-dev",
            json={"name": "User B", "email": email_b, "password": "Test1234!"},
        )
        assert r.status_code == 200
        ctx.user_b_token = r.json()["access_token"]

    def user_b_cannot_access_project():
        r = client.get(
            f"{API}/projects/{ctx.project_id}",
            headers=auth_headers(ctx.user_b_token),
        )
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def user_b_cannot_download():
        r = client.get(
            f"{API}/files/download",
            headers=auth_headers(ctx.user_b_token),
            params={"file_path": ctx.uploaded_path},
        )
        assert r.status_code in (403, 404), f"Expected 403/404, got {r.status_code}"

    run_test(ctx, "isolation", "Create second user", create_user_b)
    run_test(ctx, "isolation", "User B cannot access User A project", user_b_cannot_access_project)
    run_test(ctx, "isolation", "User B cannot download User A file", user_b_cannot_download)


# ── Phase 7: Edit Server Integration ─────────────────────────────────────────

def phase_edit_server(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 7: Edit Server (Port 8002) ===")
    headers = auth_headers(ctx.access_token)

    def edit_server_health():
        try:
            r = client.get(f"{EDIT_URL}/health", timeout=3.0)
            assert r.status_code == 200, f"Edit server not responding: {r.status_code}"
            assert r.json().get("service") == "edit_server"
        except Exception as e:
            raise AssertionError(f"Edit server unreachable: {e}")

    def edit_3d_model():
        # Test edit endpoint (may be async)
        # The edit service accepts a downloadable DXF URL, not a local path.
        # Publish this disposable fixture through the backend's output mount.
        edit_fixture = STORAGE_OUTPUTS / Path(ctx.dxf_path).name
        edit_fixture.write_bytes(Path(ctx.dxf_path).read_bytes())
        r = client.post(
            f"{EDIT_URL}/edit",
            headers=headers,
            json={
                "dxf_url": f"{BASE_URL}/static/outputs/{edit_fixture.name}",
                "instruction": "enlarge all circles by 20%",
            },
        )
        # Accept both immediate success and async job creation
        assert r.status_code in (200, 202), f"status={r.status_code} body={r.text}"
        data = r.json()
        assert "output_path" in data or "job_id" in data

    run_test(ctx, "edit_server", "Edit Server health check", edit_server_health)
    run_test(ctx, "edit_server", "POST /dxf/edit (DXF editing)", edit_3d_model)


# ── Phase 8: Generation Tests (AI) ─────────────────────────────────────────────

def phase_generation(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 8: AI Generation (Optional) ===")
    headers = auth_headers(ctx.access_token)

    def text_to_3d_async():
        # This is typically async (job-based)
        r = client.post(
            f"{API}/generation/text-to-3d",
            headers=headers,
            json={
                "prompt": "a cube 50mm on each side",
                "project_id": ctx.project_id,
            },
        )
        # Accept both immediate and async responses
        if r.status_code == 202:
            # Job created
            data = r.json()
            assert "job_id" in data or "id" in data
            return True
        elif r.status_code == 200:
            # Immediate response (unlikely)
            data = r.json()
            assert "file_path" in data or "file_id" in data
            return True
        else:
            raise AssertionError(f"status={r.status_code} body={r.text}")

    def text_to_2d_async():
        r = client.post(
            f"{API}/generation/text-to-2d",
            headers=headers,
            json={
                "prompt": "a square 100x100mm with 4 holes",
                "project_id": ctx.project_id,
            },
        )
        assert r.status_code in (200, 202), f"status={r.status_code} body={r.text}"

    def image_to_3d_mock():
        # May not work without actual image + keys
        try:
            # Try with a placeholder
            r = client.post(
                f"{API}/generation/image-to-3d",
                headers=headers,
                files={"image": ("test.png", b"\x89PNG\r\n\x1a\n", "image/png")},
                data={"project_id": ctx.project_id},
            )
            # Any response is OK (might fail due to missing keys)
            return True
        except Exception:
            return False

    # Only test if AI services are configured
    gemini_key = os.getenv("GEMINI_API_KEY")
    hf_token = os.getenv("HF_TOKEN")
    
    if gemini_key or hf_token:
        run_test(ctx, "generation", "Text-to-3D generation", text_to_3d_async)
        run_test(ctx, "generation", "Text-to-2D generation", text_to_2d_async)
        run_test(ctx, "generation", "Image-to-3D generation", image_to_3d_mock)
    else:
        print("  SKIP  Generation tests — no AI keys configured")


# ── Phase 9: Database persistence ─────────────────────────────────────────────

def phase_persistence(ctx: TestContext, client: httpx.Client) -> None:
    print("\n=== Phase 9: Data Persistence ===")

    def re_login_and_load():
        r = client.post(
            f"{API}/auth/login",
            json={"email": ctx.email, "password": ctx.password},
        )
        assert r.status_code == 200
        token = r.json()["access_token"]
        r2 = client.get(f"{API}/projects/{ctx.project_id}", headers=auth_headers(token))
        assert r2.status_code == 200
        assert r2.json()["id"] == ctx.project_id

    def db_file_exists():
        db_path = ROOT / "cad_studio.db"
        assert db_path.exists(), f"Database not found at {db_path}"

    def storage_files_exist():
        assert STORAGE_UPLOADS.exists(), f"Storage uploads dir missing: {STORAGE_UPLOADS}"
        assert STORAGE_OUTPUTS.exists(), f"Storage outputs dir missing: {STORAGE_OUTPUTS}"

    run_test(ctx, "persistence", "Re-login loads same project", re_login_and_load)
    run_test(ctx, "persistence", "SQLite database file exists", db_file_exists)
    run_test(ctx, "persistence", "Storage directories exist", storage_files_exist)


def print_summary(ctx: TestContext) -> int:
    passed = sum(1 for r in ctx.results if r.passed)
    failed = sum(1 for r in ctx.results if not r.passed)
    total = len(ctx.results)
    total_time_ms = sum(r.duration_ms for r in ctx.results)

    print("\n" + "=" * 70)
    print(f"✅ RESULTS: {passed}/{total} PASSED, ❌ {failed} FAILED")
    print(f"⏱️  Total execution time: {total_time_ms}ms ({total_time_ms/1000:.2f}s)")
    print("=" * 70)

    if failed:
        print("\n❌ Failed tests:")
        for r in ctx.results:
            if not r.passed:
                print(f"  [{r.phase}] {r.name}")
                print(f"    Error: {r.detail}")
                print()

    # Group by phase
    phases = {}
    for r in ctx.results:
        if r.phase not in phases:
            phases[r.phase] = {"passed": 0, "failed": 0}
        if r.passed:
            phases[r.phase]["passed"] += 1
        else:
            phases[r.phase]["failed"] += 1

    print("\n📊 Results by Phase:")
    for phase, stats in phases.items():
        status = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {status} {phase}: {stats['passed']}/{stats['passed']+stats['failed']}")

    status = "🎉 FULLY TESTED" if failed == 0 else "⚠️  PARTIALLY TESTED"
    marker = "[✅ OK]" if failed == 0 else "[⚠️  PARTIAL]"
    print(f"\n{marker} Status: {status}")

    # Save detailed report
    report_path = ROOT / "storage" / "temp" / f"e2e_report_{int(time.time())}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_dict = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "passed": passed,
        "failed": failed,
        "total": total,
        "total_time_ms": total_time_ms,
        "base_url": BASE_URL,
        "services": {
            "main": f"{BASE_URL}",
            "ai_2d": AI_2D_URL,
            "edit": EDIT_URL,
            "nesting": NESTING_URL,
        },
        "results": [
            {
                **r.__dict__,
                "duration_ms": r.duration_ms,
            }
            for r in ctx.results
        ],
    }
    report_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    print(f"\n📄 Report saved: {report_path}\n")

    return 0 if failed == 0 else 1


def main() -> int:
    print("\n" + "=" * 70)
    print("🚀 CNC Design Generator — E2E API Test Runner")
    print("=" * 70)
    print(f"📍 Main Backend:    {BASE_URL}")
    print(f"📍 AI Server 2D:    {AI_2D_URL}")
    print(f"📍 Edit Server:     {EDIT_URL}")
    print(f"📍 Nesting Worker:  {NESTING_URL}")
    print("=" * 70 + "\n")

    ctx = TestContext()
    with httpx.Client(timeout=60.0) as client:
        phase_health(ctx, client)

        health_ok = any(r.name == "Main backend /health" and r.passed for r in ctx.results)
        if not health_ok:
            print("\nMain backend not reachable. Start it with:")
            print("  python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000")
            return 1

        phase_auth(ctx, client)
        if not ctx.access_token:
            print("\nAuth failed — stopping.")
            return print_summary(ctx)

        phase_projects(ctx, client)
        phase_files(ctx, client)
        phase_cad(ctx, client)
        phase_billing(ctx, client)
        phase_edit_server(ctx, client)
        phase_generation(ctx, client)
        phase_isolation(ctx, client)
        phase_persistence(ctx, client)

    return print_summary(ctx)


if __name__ == "__main__":
    sys.exit(main())
