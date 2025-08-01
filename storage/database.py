from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
import os
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv('DATABASE_URL')


engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass


def get_db():
    """
    Yield a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:

    """Context manager for database sessions with proper error handling."""

    db = None
    try:
        db = SessionLocal()
        yield db
    except exc.OperationalError as e:
        print(f"Database operational error: {e}")
        raise DatabaseError("Database server is unavailable. Please try again later.")
    except exc.ArgumentError as e:
        print(f"Database configuration error: {e}")
        raise DatabaseError("Database configuration is invalid. Please contact support.")
    finally:
        if db:
            db.close()
