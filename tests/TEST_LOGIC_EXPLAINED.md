# 🧪 Test Logic Explained - How test_api.py Works

## 🎯 Core Pattern: REQUEST → PROCESS → VERIFY

كل اختبار يتبع نفس الـ pattern:

```
┌─────────────┐
│  User Clicks│ (Simulated by test)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  FRONTEND MAKES REQUEST         │
│  POST /api/v1/endpoint          │
│  Headers: {Authorization: ...}  │
│  Body: {data...}                │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  BACKEND (FastAPI)              │
│  1. Validate input              │
│  2. Check authorization         │
│  3. Query/Update Database       │
│  4. Return response             │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  TEST VERIFIES RESPONSE         │
│  1. Check status code (200/201) │
│  2. Parse JSON data             │
│  3. Assert expected fields      │
│  4. Extract values for next test│
└─────────────────────────────────┘
```

---

## 📋 Test Structure Breakdown

### **Simple Test:**
```python
def test_login():
    # 1. MAKE REQUEST
    r = client.post(
        f"{API}/auth/login",
        json={"email": "user@test.com", "password": "Test1234!"}
    )
    
    # 2. CHECK STATUS
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    
    # 3. PARSE RESPONSE
    data = r.json()  # {"access_token": "jwt...", "user": {...}}
    
    # 4. VERIFY FIELDS
    assert data.get("access_token"), "Missing access_token"
    assert data.get("user"), "Missing user object"
    
    # 5. SAVE FOR NEXT TEST
    ctx.access_token = data["access_token"]
```

### **How run_test() Works:**

```python
def run_test(ctx, phase, name, fn):
    start = time.perf_counter()  # Record start time
    try:
        fn()  # Execute test function
        ms = int((time.perf_counter() - start) * 1000)  # Calculate duration
        ctx.results.append(TestResult(
            name=name,
            phase=phase,
            passed=True,
            duration_ms=ms
        ))
        print(f"  ✅ PASS  {name} ({ms}ms)")
    except AssertionError as exc:
        # Test failed (assertion)
        print(f"  ❌ FAIL  {name} — {exc}")
    except Exception as exc:
        # Test crashed (network, JSON, etc)
        print(f"  ❌ FAIL  {name} — {type(exc).__name__}")
```

---

## 🔄 Full Test Flow Example

### **Scenario: User login → Create project → Upload file → Parse DXF**

```
Step 1: Register User
────────────────────
test_api.py:
  ↓ POST /auth/register-dev
  {"name": "Tester", "email": "test@ex.com", "password": "Test1234!"}
  
backend/app/api/auth/router.py:
  ↓ @router.post("/register-dev")
  ├─ Validate: email format, password strength
  ├─ Query DB: Check if user exists
  ├─ Create: Insert new user in DB
  ├─ Hash: Bcrypt password
  ├─ Generate: JWT access_token & refresh_token
  └─ Return: {access_token, refresh_token, user{id, email, name}}
  
test_api.py:
  ← {"access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...", ...}
  ✅ PASS Register (200 ms)
  💾 ctx.access_token = "eyJ0eXAi..."
  💾 ctx.user_id = "uuid-123"


Step 2: Create Project
──────────────────────
test_api.py:
  ↓ POST /api/v1/projects
  Headers: {"Authorization": "Bearer eyJ0eXAi..."}
  Body: {"name": "Test Project", "type": "2D"}
  
backend/app/api/projects/router.py:
  ↓ @router.post("/projects")
  ├─ Check: Authorization header valid?
  ├─ Extract: user_id from JWT token
  ├─ Validate: Project name not empty
  ├─ Query DB: Get user record
  ├─ Create: Insert into projects table
  │  INSERT INTO projects (id, name, type, user_id, created_at)
  │  VALUES (uuid, "Test Project", "2D", "uuid-123", NOW())
  ├─ Commit: DB transaction
  └─ Return: {id: "proj-456", name: "Test Project", type: "2D", user_id: "uuid-123"}
  
test_api.py:
  ← {"id": "proj-456", "name": "Test Project", ...}
  ✅ PASS Create project (145 ms)
  💾 ctx.project_id = "proj-456"


Step 3: Upload DXF File
───────────────────────
test_api.py:
  ↓ Prepare file: storage/temp/sample.dxf
  ↓ POST /api/v1/files/upload
  Headers: {"Authorization": "Bearer eyJ0eXAi..."}
  File: (binary DXF data)
  
backend/app/api/files/router.py:
  ↓ @router.post("/upload")
  ├─ Check: Authorization valid
  ├─ Extract: user_id from token
  ├─ Validate: File extension (.dxf)
  ├─ Read: File content (binary)
  ├─ Save: Copy to storage/uploads/users/{user_id}/{filename}
  ├─ Create: Record in database
  │  INSERT INTO input_files (id, user_id, project_id, path, filename, ...)
  ├─ Commit: DB transaction
  └─ Return: {file_id: "file-789", saved_path: "storage/uploads/users/...", ...}
  
test_api.py:
  ← {"file_id": "file-789", "saved_path": "storage/uploads/...", ...}
  ✅ PASS Upload DXF (320 ms)
  💾 ctx.uploaded_path = "storage/uploads/users/.../sample.dxf"


Step 4: Parse DXF
─────────────────
test_api.py:
  ↓ POST /api/v1/cad/parse-dxf
  Headers: {"Authorization": "Bearer eyJ0eXAi..."}
  Body: {"file_path": "storage/uploads/users/.../sample.dxf"}
  
backend/app/api/cad/router.py:
  ↓ @router.post("/parse-dxf")
  ├─ Check: Authorization valid
  ├─ Load: Read DXF file from disk
  ├─ Parse: Extract entities (LINES, CIRCLES, etc)
  │  FOR EACH line in DXF:
  │    IF line is "LINE": {type: "LINE", points: [...]}
  │    IF line is "CIRCLE": {type: "CIRCLE", center: [...], radius: ...}
  ├─ Build: entities list = [{type, layer, coordinates}, ...]
  ├─ Return: {status: "SUCCESS", entities: [...], bounds: {...}}
  └─ Response
  
test_api.py:
  ← {"status": "SUCCESS", "entities": [{type: "LINE", points: [...]}, ...]}
  ✅ PASS Parse DXF (89 ms)
  ✓ Verify: entities.length >= 1
```

---

## 🔐 Authorization Flow

### **How JWT Works in Tests:**

```python
# 1. LOGIN - Get token
r = client.post("/auth/login", json={...})
token = r.json()["access_token"]
# token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ..."

# 2. USE TOKEN - Include in header
headers = {"Authorization": f"Bearer {token}"}
r = client.get("/auth/me", headers=headers)

# 3. BACKEND - Verify token
@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user_id = payload["sub"]  # Extract user_id
    user = db.query(User).filter(User.id == user_id).first()
    return user
```

### **Token Structure (JWT):**

```
eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9  ← Header (base64)
.
eyJzdWIiOiJ1c2VyLWlkLWhlcmUiLCJpYXQiOjE2MzI0NTk0MjZ9  ← Payload (base64)
.
d4h8f9j2k3_signature_here  ← Signature (HMAC-SHA256)

Decoded Payload:
{
  "sub": "user-123",      ← Who (user_id)
  "iat": 1632459426,      ← When (issued at)
  "exp": 1632545826       ← Expiry
}
```

---

## 💾 Database State During Tests

### **After Complete Test Run:**

```
DATABASE: cad_studio.db
└─ users
   ├─ id: user-123
   ├─ email: e2e_tester_abc123@example.com
   ├─ password_hash: $2b$12$...
   └─ created_at: 2024-09-16 20:42:06

└─ projects
   ├─ id: proj-456
   ├─ name: "E2E Test Project"
   ├─ user_id: user-123 (FK)
   ├─ type: "2D"
   └─ created_at: 2024-09-16 20:42:10

└─ input_files
   ├─ id: file-789
   ├─ user_id: user-123 (FK)
   ├─ project_id: proj-456 (FK)
   ├─ path: "storage/uploads/users/user-123/file-789_sample.dxf"
   ├─ filename: "sample.dxf"
   └─ created_at: 2024-09-16 20:42:15

└─ users (second user)
   ├─ id: user-999
   ├─ email: e2e_userb_def456@example.com
   └─ created_at: 2024-09-16 20:42:20
```

### **Isolation Check:**
```python
# User B tries to access User A's project
def user_b_cannot_access():
    r = client.get(
        f"/api/v1/projects/{proj-456}",  ← User A's project
        headers={"Authorization": f"Bearer {user-b-token}"}
    )
    assert r.status_code == 404  ← Forbidden!
    
# Backend logic:
@router.get("/projects/{project_id}")
def get_project(project_id: str, user_id: str = Depends(get_current_user)):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id  ← ✅ Only own projects
    ).first()
    if not project:
        raise HTTPException(404)  ← 404 Not Found
```

---

## 🔄 Context Object (ctx) - Passing State Between Tests

```python
@dataclass
class TestContext:
    email: str = ""                    # User's email
    password: str = "Test1234!"        # User's password
    access_token: str = ""             # JWT token (Phase 1 → Phase 2+)
    refresh_token: str = ""            # Refresh token (Phase 1 → Phase 2+)
    user_id: str = ""                  # User ID (Phase 1 → Phase 2+)
    project_id: str = ""               # Project ID (Phase 2 → Phase 3+)
    uploaded_path: str = ""            # File path (Phase 3 → Phase 4+)
    user_b_token: str = ""             # Second user's token (Phase 6)
    results: list[TestResult] = [...]  # All test results
```

### **How it flows:**

```
Phase 1 (Auth):
  ctx.email = "e2e_tester_abc123@example.com"
  ctx.access_token = "eyJ0..."
  ctx.user_id = "user-123"
  ↓
Phase 2 (Projects):
  ctx.project_id = "proj-456"  ← Added
  (uses ctx.access_token from Phase 1)
  ↓
Phase 3 (Files):
  ctx.uploaded_path = "storage/uploads/.../sample.dxf"  ← Added
  (uses ctx.access_token from Phase 1)
  ↓
Phase 4 (CAD):
  (uses ctx.uploaded_path from Phase 3)
  (uses ctx.access_token from Phase 1)
  ↓
Phase 6 (Isolation):
  ctx.user_b_token = "eyJ0..." (new token for User B)
  (uses ctx.project_id from Phase 2 to verify User B can't access)
```

---

## ✅ Assertions - How Tests Fail/Pass

### **Common Assertions:**

```python
# 1. Status code check
assert r.status_code == 200, f"Expected 200, got {r.status_code}"
# Fails: Expected 200, got 500

# 2. Field existence
assert data.get("access_token"), "missing access_token"
# Fails: missing access_token

# 3. Field value
assert data["plan"] == "pro", f"Expected 'pro', got '{data['plan']}'"
# Fails: Expected 'pro', got 'free'

# 4. Array length
assert len(entities) >= 1, "No entities found"
# Fails: No entities found

# 5. Type check
assert isinstance(data["created_at"], str), "created_at should be string"
# Fails: created_at should be string

# 6. Range check
assert 0 <= material_usage <= 100, f"Invalid usage: {material_usage}"
# Fails: Invalid usage: 150

# 7. Boolean check
assert data["is_manifold"] is True, "Mesh should be manifold"
# Fails: Mesh should be manifold
```

---

## 🎯 Error Handling - What Happens When Test Fails

```python
def run_test(ctx, phase, name, fn):
    try:
        fn()  # Execute test
        # ✅ Success → Add PASS result
        ctx.results.append(TestResult(passed=True, ...))
        print(f"  ✅ PASS  {name}")
        
    except AssertionError as exc:
        # ❌ Assertion failed (our fault or code bug)
        ctx.results.append(TestResult(
            passed=False,
            detail=str(exc)  # The assertion message
        ))
        print(f"  ❌ FAIL  {name} — {exc}")
        # Continue to next test (don't stop)
        
    except Exception as exc:
        # ❌ Unexpected error (network, JSON, etc)
        ctx.results.append(TestResult(
            passed=False,
            detail=f"{type(exc).__name__}: {exc}"
        ))
        print(f"  ❌ FAIL  {name} — {type(exc).__name__}")
        # Continue to next test (don't stop)

# Result: Tests continue even if one fails
# This helps identify ALL problems, not just the first one
```

### **Example Failure Cascade:**

```
Phase 1: Auth
  ✅ Register (200 ms)
  ✅ Login (145 ms)
  ✅ GET /auth/me (89 ms)
  ❌ Refresh token — Expected 200, got 401
       ↑ Token refresh broken
       ↑ But we still got token from login, so continue

Phase 2: Projects
  ✅ Create project (156 ms)
    (uses token from login, not refresh)
  ✅ List projects (98 ms)
  ✅ Update project (112 ms)
  ❌ Delete to trash — 500 Internal Server Error
       ↑ Delete endpoint broken

Phase 3: Files
  ❌ Upload — Connection refused (8000 backend down)
       ↑ Backend crashed or restarted
  ❌ Download — Connection refused

Summary:
  ✅ PASSED: 10
  ❌ FAILED: 3
  Issues to fix:
    1. Refresh token endpoint
    2. Delete project endpoint
    3. Backend health
```

---

## 📊 Timing & Performance

### **How timing works:**

```python
def run_test(ctx, phase, name, fn):
    start = time.perf_counter()  # Get start time (high precision)
    
    try:
        fn()  # Execute test
    finally:
        elapsed_seconds = time.perf_counter() - start  # Calculate elapsed
        ms = int(elapsed_seconds * 1000)  # Convert to milliseconds
        
        ctx.results.append(TestResult(..., duration_ms=ms))
        print(f"  ✅ PASS  {name} ({ms}ms)")
```

### **Typical Timings:**

```
Auth tests:        50-200ms  (DB query + JWT generation)
Project CRUD:      100-300ms (DB insert/update)
File upload:       200-500ms (Network + disk I/O)
DXF parsing:       100-300ms (File read + parsing)
CAD operations:    150-400ms (Complex calculations)
Billing:           100-250ms (DB query + mock payment)
Isolation check:   80-200ms  (Auth + permission check)
```

### **Total Test Suite:**

```
25 tests × ~150ms average = 3750ms (3.75 seconds)

Typical breakdown:
  Phase 0 (Health):      ~200ms (4 × 50ms pings)
  Phase 1 (Auth):        ~600ms (4 tests)
  Phase 2 (Projects):    ~700ms (6 tests)
  Phase 3 (Files):       ~400ms (2 tests)
  Phase 4 (CAD):         ~600ms (3 tests)
  Phase 5 (Billing):     ~500ms (3 tests)
  Phase 6 (Isolation):   ~400ms (3 tests)
  Phase 7 (Persistence): ~300ms (3 tests)
  ─────────────────────────────
  Total:              ~3700ms
```

---

## 🔍 Debugging Failed Tests

### **When a test fails:**

```bash
# 1. Read the error message
❌ FAIL  Parse DXF — status=500 body=Internal Server Error

# 2. Check which endpoint failed
# → POST /api/v1/cad/parse-dxf

# 3. Verify the request was correct
# → {"file_path": "storage/uploads/users/abc/def_sample.dxf"}

# 4. Check backend logs for 500 error
# → Check backend terminal for error traceback

# 5. Verify file exists
# → Check if storage/uploads/users/abc/def_sample.dxf exists

# 6. Verify database state
# → SELECT * FROM input_files WHERE id = '...';

# 7. Run test again to see if it's flaky
# → python test_api.py
```

### **JSON Report for debugging:**

```json
{
  "name": "Parse DXF",
  "phase": "cad",
  "passed": false,
  "detail": "status=500 body=Internal Server Error",
  "duration_ms": 234
}
```

---

## 🎓 Summary - Test Lifecycle

```
START TEST RUN
   ↓
PHASE 0: Health checks
   ├─ Ping 8000 (Main)
   ├─ Ping 8001 (AI 2D)
   ├─ Ping 8002 (Edit)
   └─ Ping 8003 (Nesting)
   ↓
PHASE 1: Auth
   ├─ Register user → Get token → Save token
   ├─ Login → Verify token
   ├─ GET /auth/me → Verify user data
   └─ Refresh → Get new token
   ↓
PHASE 2: Projects
   ├─ Create → Save project_id
   ├─ List → Verify count
   ├─ Update → Change name
   ├─ Delete → Move to trash
   ├─ List trash → Verify in trash
   └─ Restore → Back to active
   ↓
PHASE 3: Files
   ├─ Upload DXF → Save file_path
   └─ Download → Verify content
   ↓
PHASE 4: CAD
   ├─ Parse DXF → Verify entities
   ├─ Inspect 3D → Verify mesh
   └─ Nesting → Verify layout
   ↓
PHASE 5: Billing
   ├─ Get status → Verify plan
   ├─ Mock checkout → Upgrade plan
   └─ Verify upgraded → Check plan
   ↓
PHASE 6: Isolation
   ├─ Create User B
   ├─ Try User B access User A project → 404
   └─ Try User B download User A file → 403/404
   ↓
PHASE 7: Persistence
   ├─ Re-login → Verify same project
   └─ Check DB file exists
   ↓
PRINT SUMMARY
   ├─ Results count
   ├─ Timings
   └─ JSON report
   ↓
END TEST RUN (✅ or ❌)
```

---

## 🎯 Key Takeaways

1. **REQUEST → RESPONSE → VERIFY** - Every test follows this pattern
2. **Context passes state** - Token from Phase 1 used in Phase 2+
3. **Tests are independent** - Each test can fail without stopping others
4. **Database is source of truth** - Verify data persists in DB
5. **Timing matters** - Measure performance for each test
6. **Isolation is critical** - User B cannot see User A's data
7. **Errors are detailed** - Know exactly what failed and why
8. **JSON reports** - Machine-readable results for automation

---

Everything makes sense now! Your tests are solid. 🚀
