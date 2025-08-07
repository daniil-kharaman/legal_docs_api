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


def create_tables() -> None:
    """Create all database tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except (exc.OperationalError, exc.ArgumentError) as e:
        print(f"Database cannot be accessed: {e}")
    except Exception as e:
        print(f"Error: {e}")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions with error handling."""
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


@contextmanager
def get_db_session() -> Generator[Session, None, None]:

    """Context manager for database sessions with error handling."""

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
