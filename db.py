from pathlib import Path

from collections.abc import Generator

from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session
from config import settings

DB_PATH = settings.database_path

engine = create_engine(
    URL.create("sqlite", database=str(DB_PATH)),
    echo=False,
    hide_parameters=True,
)

@event.listens_for(engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session