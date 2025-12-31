import sqlite3
from pathlib import Path
from typing import Iterable


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        send_to TEXT,
        program_path TEXT,
        parameters TEXT,
        batch_path TEXT,
        api_enabled INTEGER NOT NULL DEFAULT 0,
        api_method TEXT,
        api_url TEXT,
        api_headers TEXT,
        api_body TEXT,
        api_auth_type TEXT,
        api_auth_value TEXT,
        api_timeout INTEGER,
        api_retries INTEGER,
        active INTEGER NOT NULL DEFAULT 1,
        once_per_day INTEGER NOT NULL DEFAULT 0,
        autostart INTEGER NOT NULL DEFAULT 0,
        run_as_enabled INTEGER NOT NULL DEFAULT 0,
        run_as_admin INTEGER NOT NULL DEFAULT 0,
        run_as_user TEXT,
        run_as_domain TEXT,
        run_as_password TEXT,
        last_run_at TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY,
        job_id INTEGER NOT NULL,
        schedule_type TEXT NOT NULL,
        days_mask INTEGER NOT NULL DEFAULT 0,
        date TEXT,
        minute_of_day INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS run_logs (
        id INTEGER PRIMARY KEY,
        job_id INTEGER NOT NULL,
        scheduled_time TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        status TEXT NOT NULL,
        exit_code INTEGER,
        output TEXT,
        error TEXT,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_schedules_job_time ON schedules(job_id, minute_of_day)",
    "CREATE INDEX IF NOT EXISTS idx_schedules_date_time ON schedules(date, minute_of_day)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_run_logs_unique ON run_logs(job_id, scheduled_time)",
]


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        _ensure_column(conn, "jobs", "run_as_admin", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "jobs", "api_enabled", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "jobs", "api_method", "TEXT")
        _ensure_column(conn, "jobs", "api_url", "TEXT")
        _ensure_column(conn, "jobs", "api_headers", "TEXT")
        _ensure_column(conn, "jobs", "api_body", "TEXT")
        _ensure_column(conn, "jobs", "api_auth_type", "TEXT")
        _ensure_column(conn, "jobs", "api_auth_value", "TEXT")
        _ensure_column(conn, "jobs", "api_timeout", "INTEGER")
        _ensure_column(conn, "jobs", "api_retries", "INTEGER")
        conn.commit()
    finally:
        conn.close()


def execute_many(conn: sqlite3.Connection, statement: str, rows: Iterable[tuple]) -> None:
    conn.executemany(statement, rows)
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    if any(row[1] == column for row in rows):
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
