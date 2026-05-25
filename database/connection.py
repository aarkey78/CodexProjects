from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from config.settings import get_settings
from database.models import Base


def create_engine_and_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return engine, SessionLocal


def init_db() -> None:
    engine, _ = create_engine_and_session()
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator:
    _, SessionLocal = create_engine_and_session()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

