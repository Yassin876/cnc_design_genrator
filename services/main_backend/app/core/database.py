"""
Database Manager — PostgreSQL / Supabase via SQLAlchemy
Reads DATABASE_URL from environment or .env file.
Example (Supabase):
  DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
"""
import os
import uuid
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load .env from the same directory as this file or parent
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set! Please add it to services/main_backend/.env\n"
        "Example: DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    )

# Create SQLAlchemy engine (connect_args for pg SSL/timeouts)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"connect_timeout": 10} if DATABASE_URL.startswith("postgresql") else {}
)


class DatabaseManager:
    def __init__(self):
        self._init_db()

    def _execute(self, sql: str, params: dict = None, fetch: str = None):
        """Execute a SQL statement and optionally fetch results."""
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            if fetch == "one":
                return result.fetchone()
            elif fetch == "all":
                return result.fetchall()
            elif fetch == "mappings":
                return result.mappings().all()
            return None

    def _init_db(self):
        """Create tables if they don't exist (idempotent)."""
        ddl_statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                owner_id TEXT,
                user_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT '3D',
                current_version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'ACTIVE',
                is_favorite INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS project_versions (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                prompt TEXT,
                source_files TEXT,
                generated_files TEXT,
                model_metadata TEXT,
                parameters TEXT,
                validation_result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS models (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                version_id TEXT NOT NULL,
                format TEXT NOT NULL,
                file_path TEXT NOT NULL,
                preview_path TEXT,
                geometry_metadata TEXT,
                dimensions TEXT,
                material TEXT DEFAULT 'Aluminum 6061',
                units TEXT DEFAULT 'mm',
                status TEXT DEFAULT 'READY',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS input_files (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                original_name TEXT NOT NULL,
                file_type TEXT,
                mime_type TEXT,
                file_size_bytes BIGINT,
                storage_path TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS output_files (
                id TEXT PRIMARY KEY,
                job_id TEXT,
                original_name TEXT NOT NULL,
                file_type TEXT,
                storage_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                user_id TEXT,
                job_type TEXT,
                status TEXT,
                stage_name TEXT DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                design_type TEXT,
                output_format TEXT,
                text_prompt TEXT,
                input_file_id TEXT,
                output_file_id TEXT,
                processing_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
            """,
        ]
        with engine.connect() as conn:
            for stmt in ddl_statements:
                conn.execute(text(stmt))
            conn.commit()

    # ── CRUD: Users ──────────────────────────────────────────────

    def create_user(self, name, email, password_hash):
        user_id = str(uuid.uuid4())
        self._execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (:id, :name, :email, :ph)",
            {"id": user_id, "name": name, "email": email, "ph": password_hash}
        )
        return user_id

    def get_user_by_email(self, email):
        row = self._execute(
            "SELECT id, name, email, created_at FROM users WHERE email=:email",
            {"email": email}, fetch="one"
        )
        if not row:
            return None
        return {"id": row[0], "name": row[1], "email": row[2], "created_at": str(row[3])}

    def get_user_by_id(self, user_id):
        row = self._execute(
            "SELECT id, name, email, created_at FROM users WHERE id=:uid",
            {"uid": user_id}, fetch="one"
        )
        if not row:
            return None
        return {"id": row[0], "name": row[1], "email": row[2], "created_at": str(row[3])}

    # ── CRUD: Projects ───────────────────────────────────────────

    def create_project(self, user_id, name, description="", project_type="3D"):
        project_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        # Auto-create user if not exists
        existing = self._execute("SELECT id FROM users WHERE id=:uid", {"uid": user_id}, fetch="one")
        if not existing:
            self._execute(
                "INSERT INTO users (id, name, email, password_hash) VALUES (:id, :name, :email, :ph)",
                {"id": user_id, "name": "Default Engineer", "email": f"{user_id}@cncstudio.com", "ph": "hash"}
            )
        self._execute(
            "INSERT INTO projects (id, owner_id, user_id, name, description, type, current_version, status) "
            "VALUES (:id, :oid, :uid, :name, :desc, :type, 1, 'ACTIVE')",
            {"id": project_id, "oid": user_id, "uid": user_id, "name": name, "desc": description, "type": project_type}
        )
        self._execute(
            "INSERT INTO project_versions (id, project_id, version_number, prompt, source_files, generated_files, model_metadata, parameters, validation_result) "
            "VALUES (:id, :pid, 1, :prompt, :sf, :gf, :mm, :params, :vr)",
            {
                "id": version_id, "pid": project_id,
                "prompt": f"Initial creation of {name}",
                "sf": "[]", "gf": "[]", "mm": "{}", "params": "{}", "vr": "{}"
            }
        )
        return project_id

    def get_project_by_id(self, project_id):
        row = self._execute(
            "SELECT id, owner_id, name, description, type, current_version, status, COALESCE(is_favorite, false), created_at, updated_at "
            "FROM projects WHERE id=:pid",
            {"pid": project_id}, fetch="one"
        )
        if not row:
            return None
        return self._project_row_to_dict(row)

    def _project_row_to_dict(self, r):
        return {
            "id": str(r[0]), "owner_id": str(r[1]), "name": r[2], "description": r[3],
            "type": r[4], "current_version": r[5], "status": r[6],
            "is_favorite": bool(r[7]), "created_at": str(r[8]), "updated_at": str(r[9])
        }

    def get_user_projects(self, user_id, status="ACTIVE", limit=None, favorites_only=False, recent_only=False):
        sql = (
            "SELECT id, owner_id, name, description, type, current_version, status, COALESCE(is_favorite, false), created_at, updated_at "
            "FROM projects WHERE (owner_id=:uid OR user_id=:uid) "
        )
        params = {"uid": user_id}
        if favorites_only:
            sql += "AND status='ACTIVE' AND is_favorite=true "
        elif status:
            sql += "AND status=:status "
            params["status"] = status
        sql += "ORDER BY updated_at DESC "
        if limit:
            sql += "LIMIT :limit "
            params["limit"] = limit
        rows = self._execute(sql, params, fetch="all")
        return [self._project_row_to_dict(r) for r in rows] if rows else []

    def update_project(self, project_id, name=None, description=None, project_type=None, status=None, is_favorite=None):
        updates, params = [], {"pid": project_id}
        if name is not None:
            updates.append("name=:name"); params["name"] = name
        if description is not None:
            updates.append("description=:description"); params["description"] = description
        if project_type is not None:
            updates.append("type=:type"); params["type"] = project_type
        if status is not None:
            updates.append("status=:status"); params["status"] = status
        if is_favorite is not None:
            updates.append("is_favorite=:is_favorite"); params["is_favorite"] = True if is_favorite else False
        if updates:
            updates.append("updated_at=CURRENT_TIMESTAMP")
            self._execute(f"UPDATE projects SET {', '.join(updates)} WHERE id=:pid", params)

    def toggle_favorite_project(self, project_id):
        row = self._execute("SELECT COALESCE(is_favorite, false) FROM projects WHERE id=:pid", {"pid": project_id}, fetch="one")
        if not row:
            return False
        new_fav = not bool(row[0])
        self._execute("UPDATE projects SET is_favorite=:fav, updated_at=CURRENT_TIMESTAMP WHERE id=:pid", {"fav": new_fav, "pid": project_id})
        return bool(new_fav)

    def move_project_to_trash(self, project_id):
        self.update_project(project_id, status="TRASH")

    def restore_project_from_trash(self, project_id):
        self.update_project(project_id, status="ACTIVE")

    def permanently_delete_project(self, project_id):
        for tbl in ["project_versions", "models", "jobs"]:
            self._execute(f"DELETE FROM {tbl} WHERE project_id=:pid", {"pid": project_id})
        self._execute("DELETE FROM projects WHERE id=:pid", {"pid": project_id})

    def clear_user_trash(self, user_id):
        rows = self._execute(
            "SELECT id FROM projects WHERE (owner_id=:uid OR user_id=:uid) AND status='TRASH'",
            {"uid": user_id}, fetch="all"
        )
        for r in (rows or []):
            self.permanently_delete_project(r[0])

    # ── CRUD: Project Versions ───────────────────────────────────

    def create_project_version(self, project_id, prompt="", source_files=None, generated_files=None,
                                model_metadata=None, parameters=None, validation_result=None):
        version_id = str(uuid.uuid4())
        row = self._execute("SELECT current_version FROM projects WHERE id=:pid", {"pid": project_id}, fetch="one")
        new_v = (row[0] if row else 0) + 1
        self._execute(
            "INSERT INTO project_versions (id, project_id, version_number, prompt, source_files, generated_files, model_metadata, parameters, validation_result) "
            "VALUES (:id, :pid, :vn, :prompt, :sf, :gf, :mm, :params, :vr)",
            {
                "id": version_id, "pid": project_id, "vn": new_v, "prompt": prompt,
                "sf": json.dumps(source_files or []), "gf": json.dumps(generated_files or []),
                "mm": json.dumps(model_metadata or {}), "params": json.dumps(parameters or {}),
                "vr": json.dumps(validation_result or {})
            }
        )
        self._execute("UPDATE projects SET current_version=:v, updated_at=CURRENT_TIMESTAMP WHERE id=:pid", {"v": new_v, "pid": project_id})
        return version_id

    def get_project_versions(self, project_id):
        rows = self._execute(
            "SELECT id, project_id, version_number, prompt, source_files, generated_files, model_metadata, parameters, validation_result, created_at "
            "FROM project_versions WHERE project_id=:pid ORDER BY version_number DESC",
            {"pid": project_id}, fetch="all"
        )
        return [
            {
                "id": r[0], "project_id": r[1], "version_number": r[2], "prompt": r[3],
                "source_files": json.loads(r[4]) if r[4] else [],
                "generated_files": json.loads(r[5]) if r[5] else [],
                "model_metadata": json.loads(r[6]) if r[6] else {},
                "parameters": json.loads(r[7]) if r[7] else {},
                "validation_result": json.loads(r[8]) if r[8] else {},
                "created_at": str(r[9])
            }
            for r in (rows or [])
        ]

    # ── CRUD: Models ─────────────────────────────────────────────

    def log_model(self, project_id, version_id, format_type, file_path, preview_path=None,
                  geometry_metadata=None, dimensions=None, material="Aluminum 6061"):
        model_id = str(uuid.uuid4())
        self._execute(
            "INSERT INTO models (id, project_id, version_id, format, file_path, preview_path, geometry_metadata, dimensions, material, units, status) "
            "VALUES (:id, :pid, :vid, :fmt, :fp, :pp, :gm, :dim, :mat, 'mm', 'READY')",
            {"id": model_id, "pid": project_id, "vid": version_id, "fmt": format_type,
             "fp": file_path, "pp": preview_path,
             "gm": json.dumps(geometry_metadata or {}), "dim": json.dumps(dimensions or {}), "mat": material}
        )
        return model_id

    def get_models_by_project(self, project_id):
        rows = self._execute("SELECT * FROM models WHERE project_id=:pid ORDER BY created_at DESC", {"pid": project_id}, fetch="all")
        return [
            {"id": r[0], "project_id": r[1], "version_id": r[2], "format": r[3], "file_path": r[4],
             "preview_path": r[5], "geometry_metadata": json.loads(r[6]) if r[6] else {},
             "dimensions": json.loads(r[7]) if r[7] else {}, "material": r[8], "units": r[9],
             "status": r[10], "created_at": str(r[11])}
            for r in (rows or [])
        ]

    # ── CRUD: Files ──────────────────────────────────────────────

    def log_input_file(self, user_id, original_name, storage_path, file_type=None, mime_type=None, size=0):
        file_id = str(uuid.uuid4())
        self._execute(
            "INSERT INTO input_files (id, user_id, original_name, file_type, mime_type, file_size_bytes, storage_path) "
            "VALUES (:id, :uid, :name, :ft, :mt, :size, :path)",
            {"id": file_id, "uid": user_id, "name": original_name, "ft": file_type, "mt": mime_type, "size": size, "path": storage_path}
        )
        return file_id

    def log_output_file(self, job_id, original_name, storage_path, file_type=None):
        file_id = str(uuid.uuid4())
        self._execute(
            "INSERT INTO output_files (id, job_id, original_name, file_type, storage_path) VALUES (:id, :jid, :name, :ft, :path)",
            {"id": file_id, "jid": job_id, "name": original_name, "ft": file_type, "path": storage_path}
        )
        return file_id

    # ── CRUD: Jobs ───────────────────────────────────────────────

    def create_job(self, user_id, project_id=None, job_type=None, design_type=None,
                   output_format=None, text_prompt=None, input_file_id=None):
        job_id = str(uuid.uuid4())
        # Clean user_id / project_id if they are placeholder non-UUID strings like 'default_user'
        if user_id and not (isinstance(user_id, str) and len(user_id) == 36 and '-' in user_id):
            user_id = None
        if project_id and not (isinstance(project_id, str) and len(project_id) == 36 and '-' in project_id):
            project_id = None

        self._execute(
            "INSERT INTO jobs (id, user_id, project_id, job_type, design_type, output_format, text_prompt, input_file_id, status, stage_name, progress) "
            "VALUES (:id, :uid, :pid, :jt, :dt, :of, :tp, :ifid, 'queued', 'queued', 0)",
            {"id": job_id, "uid": user_id, "pid": project_id, "jt": job_type,
             "dt": design_type, "of": output_format, "tp": text_prompt, "ifid": input_file_id}
        )
        return job_id

    def update_job_status(self, job_id, status, stage_name=None, progress=None, output_file_id=None, processing_time_ms=None):
        completed_at = datetime.now().isoformat() if status in ["completed", "failed", "cancelled"] else None
        stage = stage_name or status
        prog = progress if progress is not None else (100 if status == "completed" else 0)
        self._execute(
            "UPDATE jobs SET status=:s, stage_name=:sn, progress=:prog, "
            "output_file_id=COALESCE(:ofid, output_file_id), "
            "processing_time_ms=COALESCE(:ptms, processing_time_ms), "
            "completed_at=:ca WHERE id=:jid",
            {"s": status, "sn": stage, "prog": prog, "ofid": output_file_id,
             "ptms": processing_time_ms, "ca": completed_at, "jid": job_id}
        )

    def get_job(self, job_id):
        row = self._execute(
            "SELECT j.id, j.status, j.stage_name, j.progress, j.job_type, j.design_type, j.output_format, j.text_prompt, "
            "       outf.storage_path AS output_file_path, outf.original_name AS output_filename "
            "FROM jobs j LEFT JOIN output_files outf ON j.output_file_id = outf.id WHERE j.id=:jid",
            {"jid": job_id}, fetch="one"
        )
        if not row:
            return None
        return {"id": row[0], "status": row[1], "stage_name": row[2], "progress": row[3],
                "job_type": row[4], "design_type": row[5], "output_format": row[6],
                "text_prompt": row[7], "output_file_path": row[8], "output_filename": row[9]}

    def get_user_jobs(self, user_id, limit=100):
        rows = self._execute(
            "SELECT j.id, j.job_type, j.design_type, j.output_format, j.status, j.stage_name, j.progress, j.text_prompt, j.created_at, "
            "       inf.original_name AS input_filename, outf.original_name AS output_filename, outf.storage_path AS output_file_path "
            "FROM jobs j LEFT JOIN input_files inf ON j.input_file_id = inf.id "
            "LEFT JOIN output_files outf ON j.output_file_id = outf.id "
            "WHERE j.user_id=:uid ORDER BY j.created_at DESC LIMIT :lim",
            {"uid": user_id, "lim": limit}, fetch="all"
        )
        return [
            {"id": r[0], "job_type": r[1], "design_type": r[2], "output_format": r[3],
             "status": r[4], "stage_name": r[5], "progress": r[6], "text_prompt": r[7],
             "created_at": str(r[8]), "input_filename": r[9], "output_filename": r[10], "output_file_path": r[11]}
            for r in (rows or [])
        ]

    def clear_user_history(self, user_id):
        self._execute("DELETE FROM jobs WHERE user_id=:uid", {"uid": user_id})
