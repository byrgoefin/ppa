"""Database engine, session factory, declarative base, and FastAPI dependency."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# PostgreSQL connection URL from environment; no SQLite fallback in this app.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://pp_user:pp_password@localhost:5432/elite_powerplay",
)

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """FastAPI dependency that yields a database session and closes it on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
