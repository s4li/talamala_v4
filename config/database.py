"""
TalaMala v4 - Database Configuration
=====================================
Engine, SessionLocal, Base, and get_db dependency.
All models across all modules inherit from this Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,  # Refresh connections every 30 minutes
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a database session, auto-closes after request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
