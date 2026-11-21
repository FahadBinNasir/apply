import os
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from app.db.models import Base

DEFAULT_DB_PATH = Path("app_data/db/apply.sqlite")


def get_db_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"


def create_db_engine(db_url: str | None = None):
    url = db_url or get_db_url()
    connect_args = {}
    if "sqlite" in url:
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args)

    if "sqlite" in url:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_db(engine=None):
    eng = engine or create_db_engine()
    Base.metadata.create_all(bind=eng)
    # Also initialize FTS5
    if "sqlite" in str(eng.url):
        with eng.connect() as conn:
            conn.exec_driver_sql("""
                CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5(
                    job_id UNINDEXED,
                    title,
                    company,
                    field,
                    skills_text,
                    location_text
                );
            """)
            conn.commit()
    return eng
