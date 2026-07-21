import sqlite3
import uuid
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="cad_studio.db"):
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

            # Projects Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

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
            # (Defined before jobs for FK if needed, but ERD shows job_id references job)
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
            
            conn.commit()

    # --- CRUD Operations ---

    def create_user(self, name, email, password_hash):
        user_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
                (user_id, name, email, password_hash)
            )
            conn.commit()
        return user_id

    def create_project(self, user_id, name, description=""):
        project_id = str(uuid.uuid4())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO projects (id, user_id, name, description) VALUES (?, ?, ?, ?)",
                (project_id, user_id, name, description)
            )
            conn.commit()
        return project_id

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
            completed_at = datetime.now().isoformat() if status in ["COMPLETED", "FAILED"] else None
            
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

    # --- Convenience get methods ---

    def get_user_by_email(self, email):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            return cursor.fetchone()

    def get_latest_jobs(self, limit=10):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,))
            return cursor.fetchall()

    def get_user_by_id(self, user_id):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, email, created_at FROM users WHERE id=?", (user_id,))
            return cursor.fetchone()

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

