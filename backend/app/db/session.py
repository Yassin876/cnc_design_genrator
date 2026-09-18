from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

db_url = settings.sqlalchemy_database_url

# Configure connect_args for SQLite to handle multi-threaded FastAPI execution
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine = create_engine(
    db_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI Dependency to yield a database session per request with automatic cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """
    Initialize database tables if they don't exist.
    Also ensures missing columns are safely added to existing SQLite tables.
    """
    from backend.app.db.base import Base
    # Ensure all models are loaded
    import backend.app.models.user  # noqa: F401
    import backend.app.models.otp  # noqa: F401
    import backend.app.models.project  # noqa: F401
    import backend.app.models.payment  # noqa: F401
    import backend.app.models.payment_method  # noqa: F401
    import backend.app.models.paddle_event  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Safe column migration for SQLite
    with engine.connect() as conn:
        try:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(users)"))
            existing_columns = {row[1] for row in result.fetchall()}
            
            column_defs = [
                ("paddle_customer_id", "TEXT"),
                ("paddle_subscription_id", "TEXT"),
                ("subscription_status", "TEXT DEFAULT 'active'"),
                ("next_billing_date", "DATETIME"),
                ("cancel_url", "TEXT"),
                ("update_url", "TEXT"),
            ]
            for col_name, col_type in column_defs:
                if col_name not in existing_columns:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
        except Exception:
            pass
