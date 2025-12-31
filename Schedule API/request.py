from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any


def perform_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: str,
    auth_type: str,
    auth_value: str,
    timeout: int,
    retries: int,
) -> dict[str, Any]:
    data = None
    if body and method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        data = body.encode("utf-8")
        headers = dict(headers)
        headers.setdefault("Content-Type", "application/json")

    headers = dict(headers or {})
    if auth_type == "Bearer" and auth_value:
        headers["Authorization"] = f"Bearer {auth_value}"
    if auth_type == "Basic" and auth_value:
        token = base64.b64encode(auth_value.encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    attempts = max(1, retries + 1)
    timeout = timeout or 30
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8", errors="replace")
                return {"status": response.status, "response": text}
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            return {"status": exc.code, "response": text, "error": str(exc)}
        except Exception as exc:
            if attempt < attempts - 1:
                time.sleep(1)
                continue
            return {"status": 0, "response": "", "error": str(exc)}
