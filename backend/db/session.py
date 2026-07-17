"""Database engine, session factory, declarative base, and FastAPI dependency."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# PostgreSQL connection URL from environment; no SQLite fallback in this app.
# Rewrite postgresql:// → postgresql+psycopg:// so SQLAlchemy uses the psycopg3
# driver (psycopg[binary]) which supports Python 3.12+.
_raw_url: str = os.getenv(
    "DATABASE_URL",
    "postgresql://pp_user:pp_password@localhost:5432/elite_powerplay",
)
DATABASE_URL = _raw_url.replace(
    "postgresql://", "postgresql+psycopg://", 1
).replace(
    "postgresql+psycopg2://", "postgresql+psycopg://", 1
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
