from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .windows import unprotect_string


@dataclass(frozen=True)
class Job:
    id: int
    name: str
    description: str
    send_to: str
    program_path: str
    parameters: str
    batch_path: str
    api_enabled: bool
    api_method: str
    api_url: str
    api_headers: str
    api_body: str
    api_auth_type: str
    api_auth_value: str
    api_timeout: int
    api_retries: int
    active: bool
    once_per_day: bool
    autostart: bool
    run_as_enabled: bool
    run_as_admin: bool
    run_as_user: str
    run_as_domain: str
    run_as_password: str
    last_run_at: Optional[datetime]

    @staticmethod
    def from_row(row) -> "Job":
        password = row["run_as_password"] or ""
        if password:
            password = unprotect_string(password)
        return Job(
            id=row["id"],
            name=row["name"] or "",
            description=row["description"] or "",
            send_to=row["send_to"] or "",
            program_path=row["program_path"] or "",
            parameters=row["parameters"] or "",
            batch_path=row["batch_path"] or "",
            api_enabled=bool(row["api_enabled"]),
            api_method=row["api_method"] or "",
            api_url=row["api_url"] or "",
            api_headers=row["api_headers"] or "",
            api_body=row["api_body"] or "",
            api_auth_type=row["api_auth_type"] or "",
            api_auth_value=row["api_auth_value"] or "",
            api_timeout=int(row["api_timeout"] or 0),
            api_retries=int(row["api_retries"] or 0),
            active=bool(row["active"]),
            once_per_day=bool(row["once_per_day"]),
            autostart=bool(row["autostart"]),
            run_as_enabled=bool(row["run_as_enabled"]),
            run_as_admin=bool(row["run_as_admin"]),
            run_as_user=row["run_as_user"] or "",
            run_as_domain=row["run_as_domain"] or "",
            run_as_password=password,
            last_run_at=_parse_dt(row["last_run_at"]),
        )


@dataclass(frozen=True)
class ScheduleSlot:
    id: int
    job_id: int
    schedule_type: str
    days_mask: int
    date: Optional[str]
    minute_of_day: int
    active: bool

    @staticmethod
    def from_row(row) -> "ScheduleSlot":
        return ScheduleSlot(
            id=row["id"],
            job_id=row["job_id"],
            schedule_type=row["schedule_type"],
            days_mask=row["days_mask"],
            date=row["date"],
            minute_of_day=row["minute_of_day"],
            active=bool(row["active"]),
        )


@dataclass(frozen=True)
class RunLog:
    id: int
    job_id: int
    scheduled_time: datetime
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str
    exit_code: Optional[int]
    output: str
    error: str

    @staticmethod
    def from_row(row) -> "RunLog":
        return RunLog(
            id=row["id"],
            job_id=row["job_id"],
            scheduled_time=_parse_dt(row["scheduled_time"]),
            start_time=_parse_dt(row["start_time"]),
            end_time=_parse_dt(row["end_time"]),
            status=row["status"],
            exit_code=row["exit_code"],
            output=row["output"] or "",
            error=row["error"] or "",
        )


@dataclass(frozen=True)
class RunLogEntry:
    job_id: int
    job_name: str
    scheduled_time: datetime
    status: str
    exit_code: Optional[int]

    @staticmethod
    def from_row(row) -> "RunLogEntry":
        return RunLogEntry(
            job_id=row["job_id"],
            job_name=row["job_name"] or "",
            scheduled_time=_parse_dt(row["scheduled_time"]),
            status=row["status"],
            exit_code=row["exit_code"],
        )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value)
