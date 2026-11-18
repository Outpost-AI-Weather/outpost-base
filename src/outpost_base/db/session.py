"""Database engine and session setup."""

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from outpost_base.config import DATABASE_URL
from outpost_base.db import models  # noqa: F401  (loads the table definitions)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_and_tables():
    """Create the database file and all tables if they don't exist yet."""
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(DATABASE_URL.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """Provide a database session, used by the API later."""
    with Session(engine) as session:
        yield session
