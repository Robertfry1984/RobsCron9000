from __future__ import annotations

from pathlib import Path


def load_env() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    env_path = root / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def get_env(key: str, default: str = "") -> str:
    values = load_env()
    return values.get(key, default)
