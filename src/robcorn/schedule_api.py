from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def perform_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: str,
    auth_type: str = "",
    auth_value: str = "",
    timeout: int = 0,
    retries: int = 0,
) -> dict[str, Any]:
    module = _load_module()
    return module.perform_request(method, url, headers, body, auth_type, auth_value, timeout, retries)


def _load_module():
    root = Path(__file__).resolve().parents[2]
    path = root / "Schedule API" / "request.py"
    spec = importlib.util.spec_from_file_location("schedule_api_request", path)
    if spec is None or spec.loader is None:
        raise ImportError("Schedule API backend not found.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
