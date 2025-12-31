from __future__ import annotations

from pathlib import Path


def app_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    return app_root() / "data"


def logs_dir() -> Path:
    return app_root() / "logs"


def db_path() -> Path:
    return data_dir() / "robcorn.sqlite3"
