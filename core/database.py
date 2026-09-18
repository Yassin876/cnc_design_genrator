import sqlite3
import uuid
from datetime import datetime
import json
import os
from core.paths import DEFAULT_DB_FILE

class DatabaseManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            self.db_path = str(DEFAULT_DB_FILE)
        elif not os.path.isabs(db_path):
            self.db_path = os.path.abspath(os.path.join(os.path.dirname(str(DEFAULT_DB_FILE)), db_path))
        else:
            self.db_path = db_path
        self._init_db()


    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Users Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("PRAGMA table_info(users)")
            user_cols = [col[1] for col in cursor.fetchall()]
            if 'avatar_url' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
            if 'plan' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'free'")
            if 'requests_used_current_cycle' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN requests_used_current_cycle INTEGER DEFAULT 0")
            if 'cycle_start_date' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN cycle_start_date TIMESTAMP")
            if 'cycle_end_date' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN cycle_end_date TIMESTAMP")
            if 'is_admin' not in user_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")

            # Payments Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    user_name TEXT,
                    user_email TEXT,
                    plan_requested TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    method TEXT NOT NULL,
                    proof_reference TEXT,
                    proof_image_path TEXT,
                    status TEXT DEFAULT 'pending_approval',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewed_by TEXT,
                    admin_notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Projects Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    type TEXT DEFAULT '3D',
                    status TEXT DEFAULT 'ACTIVE',
                    is_favorite INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Ensure columns exist in projects table
            cursor.execute("PRAGMA table_info(projects)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'type' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN type TEXT DEFAULT '3D'")
            if 'status' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN status TEXT DEFAULT 'ACTIVE'")
            if 'is_favorite' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN is_favorite INTEGER DEFAULT 0")
            if 'file_path' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN file_path TEXT")
            if 'is_deleted' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN is_deleted INTEGER DEFAULT 0")
            if 'deleted_at' not in cols:
                cursor.execute("ALTER TABLE projects ADD COLUMN deleted_at TIMESTAMP")

            # Input Files Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS input_files (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    original_name TEXT NOT NULL,
                    file_type TEXT,
                    mime_type TEXT,
                    file_size_bytes BIGINT,
                    storage_path TEXT NOT NULL,
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            # Output Files Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS output_files (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    original_name TEXT NOT NULL,
                    file_type TEXT,
                    storage_path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Jobs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT,
                    user_id TEXT,
                    job_type TEXT,
                    status TEXT,
                    design_type TEXT,
                    output_format TEXT,
                    text_prompt TEXT,
                    input_file_id TEXT,
                    output_file_id TEXT,
                    processing_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id),
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (input_file_id) REFERENCES input_files (id),
                    FOREIGN KEY (output_file_id) REFERENCES output_files (id)
                )
            """)

            # Conversations Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    design_type TEXT DEFAULT '2D',
                    title TEXT NOT NULL,
                    active_file_path TEXT,
                    is_pinned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Chat Messages Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    design_type TEXT DEFAULT '2D',
                    sender TEXT NOT NULL,
                    text TEXT,
                    attachments_json TEXT,
                    timestamp TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("PRAGMA table_info(chat_messages)")
            chat_cols = [col[1] for col in cursor.fetchall()]
            if 'attachments_json' not in chat_cols:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN attachments_json TEXT")
            if 'timestamp' not in chat_cols:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN timestamp TEXT")
            if 'design_type' not in chat_cols:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN design_type TEXT DEFAULT '2D'")
            if 'conversation_id' not in chat_cols:
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN conversation_id TEXT")



            # Project Versions Table
            cursor.execute("""
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
            """)
            
            conn.commit()

    # --- Users CRUD ---

    def create_user(self, name, email, password_hash):
        user_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            cols = [col[1] for col in cursor.fetchall()]
            data = {
                "id": user_id,
                "name": name,
                "email": email,
                "password_hash": password_hash,
            }
            if "is_email_verified" in cols:
                data["is_email_verified"] = 1
            if "is_active" in cols:
                data["is_active"] = 1
            if "created_at" in cols:
                data["created_at"] = now
            if "updated_at" in cols:
                data["updated_at"] = now

            col_names = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            query = f"INSERT INTO users ({col_names}) VALUES ({placeholders})"
            cursor.execute(query, tuple(data.values()))
            conn.commit()
        return user_id



    def get_user_by_email(self, email):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            return cursor.fetchone()

    def get_user_by_id(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, created_at FROM users WHERE id=?", (user_id,))
            return cursor.fetchone()

    # --- Projects CRUD ---

    def create_project(self, user_id, name, description="", project_type="3D", file_path=None):
        project_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO projects (id, user_id, name, description, type, status, is_favorite, file_path, is_deleted, deleted_at, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, 'ACTIVE', 0, ?, 0, NULL, ?, ?)""",
                (project_id, user_id, name, description, project_type, file_path, now, now)
            )
            conn.commit()
        
        # Create initial version for the project
        self.create_project_version(
            project_id=project_id,
            prompt=f"Initial project: {name}",
            source_files=[],
            generated_files=[],
            model_metadata={},
            parameters={}
        )
        
        return project_id

    def get_user_projects(self, user_id, status=None, limit=None, favorites_only=False, recent_only=False, filter_mode=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = """SELECT id, user_id as owner_id, name, description, COALESCE(type, '3D') as type, 
                              COALESCE(status, 'ACTIVE') as status, COALESCE(is_favorite, 0) as is_favorite,
                              file_path, COALESCE(is_deleted, 0) as is_deleted, deleted_at,
                              created_at, updated_at FROM projects WHERE user_id=?"""
            params = [user_id]

            if filter_mode == "trash":
                query += " AND (COALESCE(is_deleted, 0) = 1 OR status = 'TRASH')"
            elif filter_mode == "favorites":
                query += " AND COALESCE(is_deleted, 0) = 0 AND COALESCE(status, 'ACTIVE') != 'TRASH' AND is_favorite = 1"
            elif filter_mode == "recent":
                query += " AND COALESCE(is_deleted, 0) = 0 AND COALESCE(status, 'ACTIVE') != 'TRASH'"
            elif filter_mode == "all":
                query += " AND COALESCE(is_deleted, 0) = 0 AND COALESCE(status, 'ACTIVE') != 'TRASH'"
            else:
                if status == "TRASH":
                    query += " AND (COALESCE(is_deleted, 0) = 1 OR status = 'TRASH')"
                elif status:
                    query += " AND COALESCE(is_deleted, 0) = 0 AND COALESCE(status, 'ACTIVE') = ?"
                    params.append(status)
                else:
                    query += " AND COALESCE(is_deleted, 0) = 0"

                if favorites_only:
                    query += " AND is_favorite = 1"

            query += " ORDER BY updated_at DESC"
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "owner_id": r[1],
                    "name": r[2],
                    "description": r[3],
                    "type": r[4],
                    "status": r[5],
                    "is_favorite": bool(r[6]),
                    "file_path": r[7],
                    "is_deleted": bool(r[8]),
                    "deleted_at": r[9],
                    "created_at": r[10],
                    "updated_at": r[11],
                }
                for r in rows
            ]

    def get_project_by_id(self, project_id, user_id=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute(
                    """SELECT id, user_id as owner_id, name, description, COALESCE(type, '3D') as type, 
                              COALESCE(status, 'ACTIVE') as status, COALESCE(is_favorite, 0) as is_favorite,
                              file_path, COALESCE(is_deleted, 0) as is_deleted, deleted_at,
                              created_at, updated_at FROM projects WHERE id=? AND user_id=?""",
                    (project_id, user_id)
                )
            else:
                cursor.execute(
                    """SELECT id, user_id as owner_id, name, description, COALESCE(type, '3D') as type, 
                              COALESCE(status, 'ACTIVE') as status, COALESCE(is_favorite, 0) as is_favorite,
                              file_path, COALESCE(is_deleted, 0) as is_deleted, deleted_at,
                              created_at, updated_at FROM projects WHERE id=?""",
                    (project_id,)
                )
            r = cursor.fetchone()
            if not r:
                return None
            return {
                "id": r[0],
                "owner_id": r[1],
                "name": r[2],
                "description": r[3],
                "type": r[4],
                "status": r[5],
                "is_favorite": bool(r[6]),
                "file_path": r[7],
                "is_deleted": bool(r[8]),
                "deleted_at": r[9],
                "created_at": r[10],
                "updated_at": r[11],
            }

    def update_project(self, project_id, name=None, description=None, project_type=None, status=None, is_favorite=None, file_path=None, is_deleted=None, deleted_at=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            if name is not None:
                cursor.execute("UPDATE projects SET name=?, updated_at=? WHERE id=?", (name, now, project_id))
            if description is not None:
                cursor.execute("UPDATE projects SET description=?, updated_at=? WHERE id=?", (description, now, project_id))
            if project_type is not None:
                cursor.execute("UPDATE projects SET type=?, updated_at=? WHERE id=?", (project_type, now, project_id))
            if status is not None:
                cursor.execute("UPDATE projects SET status=?, updated_at=? WHERE id=?", (status, now, project_id))
            if is_favorite is not None:
                cursor.execute("UPDATE projects SET is_favorite=?, updated_at=? WHERE id=?", (1 if is_favorite else 0, now, project_id))
            if file_path is not None:
                cursor.execute("UPDATE projects SET file_path=?, updated_at=? WHERE id=?", (file_path, now, project_id))
            if is_deleted is not None:
                cursor.execute("UPDATE projects SET is_deleted=?, updated_at=? WHERE id=?", (1 if is_deleted else 0, now, project_id))
            if deleted_at is not None:
                cursor.execute("UPDATE projects SET deleted_at=?, updated_at=? WHERE id=?", (deleted_at, now, project_id))
            conn.commit()

    def toggle_favorite_project(self, project_id):
        proj = self.get_project_by_id(project_id)
        if not proj:
            return False
        new_fav = not proj["is_favorite"]
        # Note: favorite is updated without altering is_deleted or deleted_at
        self.update_project(project_id, is_favorite=new_fav)
        return new_fav

    def move_project_to_trash(self, project_id):
        now = datetime.now().isoformat()
        self.update_project(project_id, status="TRASH", is_deleted=True, deleted_at=now)

    def restore_project_from_trash(self, project_id):
        self.update_project(project_id, status="ACTIVE", is_deleted=False, deleted_at="")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE projects SET deleted_at=NULL WHERE id=?", (project_id,))
            conn.commit()

    def permanently_delete_project(self, project_id):
        # Must only delete if project was in trash
        proj = self.get_project_by_id(project_id)
        if not proj:
            return False
        if not proj.get("is_deleted") and proj.get("status") != "TRASH":
            raise ValueError("Project must be in trash before permanent deletion")

        # Delete physical CAD file (DXF or STL) if exists
        file_path = proj.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Warning: could not delete physical project file {file_path}: {e}")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id=?", (project_id,))
            conn.commit()
        return True

    def clear_user_trash(self, user_id):
        trash_projects = self.get_user_projects(user_id, filter_mode="trash")
        for p in trash_projects:
            try:
                self.permanently_delete_project(p["id"])
            except Exception:
                pass

    # --- Versions ---

    def get_project_versions(self, project_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, project_id, version_number, prompt, source_files, generated_files, model_metadata, parameters, validation_result, created_at FROM project_versions WHERE project_id=? ORDER BY version_number ASC", (project_id,))
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "project_id": r[1],
                    "version_number": r[2],
                    "prompt": r[3],
                    "source_files": json.loads(r[4] or "[]"),
                    "generated_files": json.loads(r[5] or "[]"),
                    "model_metadata": json.loads(r[6] or "{}"),
                    "parameters": json.loads(r[7] or "{}"),
                    "validation_result": json.loads(r[8] or "{}"),
                    "created_at": r[9]
                }
                for r in rows
            ]

    def create_project_version(self, project_id, prompt, source_files=None, generated_files=None, model_metadata=None, parameters=None):
        v_id = str(uuid.uuid4())
        versions = self.get_project_versions(project_id)
        next_ver = len(versions) + 1
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO project_versions 
                   (id, project_id, version_number, prompt, source_files, generated_files, model_metadata, parameters, validation_result) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    v_id, project_id, next_ver, prompt,
                    json.dumps(source_files or []),
                    json.dumps(generated_files or []),
                    json.dumps(model_metadata or {}),
                    json.dumps(parameters or {}),
                    json.dumps({"valid": True})
                )
            )
            conn.commit()
        return v_id

    def get_models_by_project(self, project_id):
        return []

    # --- Conversations CRUD ---

    def create_conversation(self, user_id: str, project_id: str, design_type: str = "2D", title: str = "محادثة جديدة", active_file_path: str = None) -> str:
        conv_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversations (id, user_id, project_id, design_type, title, active_file_path)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (conv_id, user_id, project_id, design_type, title, active_file_path)
            )
            conn.commit()
        return conv_id

    def get_user_conversations(self, user_id: str, project_id: str, design_type: str = "2D") -> list:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, user_id, project_id, design_type, title, active_file_path, is_pinned, created_at, updated_at
                   FROM conversations
                   WHERE user_id=? AND project_id=? AND design_type=?
                   ORDER BY is_pinned DESC, updated_at DESC""",
                (user_id, project_id, design_type)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "user_id": r[1],
                    "project_id": r[2],
                    "design_type": r[3],
                    "title": r[4],
                    "active_file_path": r[5],
                    "is_pinned": bool(r[6]),
                    "created_at": r[7],
                    "updated_at": r[8]
                }
                for r in rows
            ]

    def update_conversation(self, conv_id: str, title: str = None, active_file_path: str = None, is_pinned: bool = None) -> bool:
        updates = []
        params = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if active_file_path is not None:
            updates.append("active_file_path = ?")
            params.append(active_file_path)
        if is_pinned is not None:
            updates.append("is_pinned = ?")
            params.append(1 if is_pinned else 0)
        
        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(conv_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0

    def delete_conversation(self, conv_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ?", (conv_id,))
            cursor.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()
            return True

    def get_conversation_messages(self, conv_id: str) -> list:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, sender, text, attachments_json, timestamp, conversation_id
                   FROM chat_messages
                   WHERE conversation_id = ?
                   ORDER BY created_at ASC""",
                (conv_id,)
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "sender": r[1],
                    "text": r[2],
                    "attachments": json.loads(r[3] or "[]"),
                    "timestamp": r[4],
                    "conversation_id": r[5]
                }
                for r in rows
            ]

    # --- Chat Messages ---

    def get_chat_history(self, user_id, project_id, design_type="2D", conversation_id=None):
        if conversation_id:
            return self.get_conversation_messages(conversation_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if design_type:
                cursor.execute(
                    "SELECT id, sender, text, attachments_json, timestamp, conversation_id FROM chat_messages WHERE user_id=? AND project_id=? AND design_type=? ORDER BY created_at ASC",
                    (user_id, project_id, design_type)
                )
            else:
                cursor.execute(
                    "SELECT id, sender, text, attachments_json, timestamp, conversation_id FROM chat_messages WHERE user_id=? AND project_id=? ORDER BY created_at ASC",
                    (user_id, project_id)
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "sender": r[1],
                    "text": r[2],
                    "attachments": json.loads(r[3] or "[]"),
                    "timestamp": r[4],
                    "conversation_id": r[5]
                }
                for r in rows
            ]

    def save_chat_message(self, user_id, project_id, design_type, sender, text, attachments=None, conversation_id=None):
        if not (text and text.strip()) and not attachments:
            return None
        import json
        ts = datetime.now().strftime("%I:%M %p")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            msg_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO chat_messages (id, user_id, project_id, design_type, sender, text, attachments_json, timestamp, conversation_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (msg_id, user_id, project_id, design_type, sender, text or "", json.dumps(attachments or []), ts, conversation_id)
            )
            if conversation_id:
                cursor.execute("UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (conversation_id,))
            conn.commit()
            return msg_id





    def clear_chat_history(self, user_id, project_id, design_type="2D"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM chat_messages WHERE user_id=? AND project_id=? AND design_type=?",
                (user_id, project_id, design_type)
            )
            conn.commit()

    # --- Files & Jobs ---

    def log_input_file(self, user_id, original_name, storage_path, file_type=None, mime_type=None, size=0):
        file_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO input_files 
                   (id, user_id, original_name, file_type, mime_type, file_size_bytes, storage_path) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (file_id, user_id, original_name, file_type, mime_type, size, storage_path)
            )
            conn.commit()
        return file_id

    def create_job(self, user_id, project_id=None, job_type=None, design_type=None, output_format=None, text_prompt=None, input_file_id=None):
        job_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO jobs 
                   (id, user_id, project_id, job_type, design_type, output_format, text_prompt, input_file_id, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, user_id, project_id, job_type, design_type, output_format, text_prompt, input_file_id, "PENDING")
            )
            conn.commit()
        return job_id

    def update_job_status(self, job_id, status, output_file_id=None, processing_time_ms=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            completed_at = datetime.now().isoformat() if status in ["COMPLETED", "FAILED", "completed", "failed"] else None
            
            if output_file_id and processing_time_ms is not None:
                cursor.execute(
                    "UPDATE jobs SET status=?, output_file_id=?, processing_time_ms=?, completed_at=? WHERE id=?",
                    (status, output_file_id, processing_time_ms, completed_at, job_id)
                )
            else:
                cursor.execute(
                    "UPDATE jobs SET status=?, completed_at=? WHERE id=?",
                    (status, completed_at, job_id)
                )
            conn.commit()

    def get_job(self, job_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT j.id, j.project_id, j.user_id, j.job_type, j.status, j.design_type, j.output_format, j.text_prompt, "
                "       outf.storage_path, outf.original_name "
                "FROM jobs j "
                "LEFT JOIN output_files outf ON j.output_file_id = outf.id OR (outf.job_id = j.id) "
                "WHERE j.id=? ORDER BY outf.created_at DESC LIMIT 1",
                (job_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "project_id": row[1],
                "user_id": row[2],
                "job_type": row[3],
                "status": row[4],
                "design_type": row[5],
                "output_format": row[6],
                "text_prompt": row[7],
                "output_file_path": row[8],
                "output_filename": row[9],
            }

    def log_output_file(self, job_id, original_name, storage_path, file_type=None):
        file_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO output_files (id, job_id, original_name, file_type, storage_path) VALUES (?, ?, ?, ?, ?)",
                (file_id, job_id, original_name, file_type, storage_path)
            )
            conn.commit()
        return file_id

    def get_latest_jobs(self, limit=10):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            return cursor.fetchall()

    def get_user_jobs(self, user_id, limit=100):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT j.id, j.job_type, j.design_type, j.output_format, j.status, j.text_prompt, j.created_at, "
                "       inf.original_name AS input_filename, outf.original_name AS output_filename, outf.storage_path AS output_file_path "
                "FROM jobs j "
                "LEFT JOIN input_files inf ON j.input_file_id = inf.id "
                "LEFT JOIN output_files outf ON j.output_file_id = outf.id "
                "WHERE j.user_id=? "
                "ORDER BY j.created_at DESC LIMIT ?",
                (user_id, limit)
            )
            return cursor.fetchall()

    def delete_job(self, job_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id=?", (job_id,))
            conn.commit()

    def clear_user_history(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE user_id=?", (user_id,))
            conn.commit()
