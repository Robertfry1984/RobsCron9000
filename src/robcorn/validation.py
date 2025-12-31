from __future__ import annotations

from pathlib import Path


def validate_job_targets(program_path: str, batch_path: str) -> list[str]:
    errors = []
    if not program_path and not batch_path:
        errors.append("Either a program path or a batch file path is required.")
        return errors
    if program_path.startswith("tool:"):
        return errors
    if program_path and not Path(program_path).exists():
        errors.append("Program path does not exist.")
    if batch_path and not Path(batch_path).exists():
        errors.append("Batch file path does not exist.")
    return errors


def validate_send_to(send_to: str) -> list[str]:
    if not send_to:
        return []
    if "@" not in send_to and ":" not in send_to:
        return ["Send-to value looks invalid."]
    return []


def validate_run_as(enabled: bool, admin: bool, user: str, password: str) -> list[str]:
    if not enabled:
        return []
    if admin:
        return []
    errors = []
    if not user:
        errors.append("Run-as user is required when RunAs is enabled.")
    if not password:
        errors.append("Run-as password is required when RunAs is enabled.")
    return errors


def validate_api_request(enabled: bool, method: str, url: str) -> list[str]:
    if not enabled:
        return []
    errors = []
    if not method:
        errors.append("API method is required when Send API request is enabled.")
    if not url:
        errors.append("API URL is required when Send API request is enabled.")
    return errors


def validate_api_auth(enabled: bool, auth_type: str, auth_value: str) -> list[str]:
    if not enabled:
        return []
    if not auth_type or auth_type == "None":
        return []
    errors = []
    if not auth_value:
        errors.append("API auth value is required when auth is enabled.")
    if auth_type == "Basic" and ":" not in auth_value:
        errors.append("Basic auth value must be in 'user:password' format.")
    return errors
