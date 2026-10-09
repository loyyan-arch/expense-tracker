from pathlib import Path

from sqlalchemy import URL, create_engine, event
from sqlalchemy.orm import DeclarativeBase

DB_PATH = Path(__file__).resolve().parent / "expenses.db"

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