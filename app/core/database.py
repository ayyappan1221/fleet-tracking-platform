"""Database engine, session factory, and the ORM base class."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

_kwargs: dict = {"echo": settings.DEBUG}

if settings.DATABASE_URL.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}
elif settings.DATABASE_URL.startswith("postgresql"):
    _kwargs["pool_pre_ping"] = True

engine = create_engine(settings.DATABASE_URL, **_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""


def get_db():
    """Yield a database session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
