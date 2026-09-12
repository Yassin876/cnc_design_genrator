from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

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
