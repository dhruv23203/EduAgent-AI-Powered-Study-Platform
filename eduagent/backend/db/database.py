import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./eduagent.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite()


def _migrate_sqlite() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as connection:
        for table in ("quiz_questions", "quiz_attempts", "study_task_completions"):
            columns = {row[1] for row in connection.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            if "plan_id" not in columns:
                connection.execute(text(f"ALTER TABLE {table} ADD COLUMN plan_id INTEGER"))
                connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_plan_id ON {table} (plan_id)"))
            if table == "quiz_attempts" and "quiz_run_id" not in columns:
                connection.execute(text("ALTER TABLE quiz_attempts ADD COLUMN quiz_run_id TEXT"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_quiz_attempts_quiz_run_id ON quiz_attempts (quiz_run_id)"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
