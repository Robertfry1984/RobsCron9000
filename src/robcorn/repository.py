from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from . import db
from .models import Job, RunLogEntry, ScheduleSlot
from .windows import protect_string


class Repository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    @property
    def db_path(self) -> Path:
        return self._db_path

    def init(self) -> None:
        db.init_db(self._db_path)

    def list_jobs(self) -> list[Job]:
        conn = db.connect(self._db_path)
        try:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id").fetchall()
            return [Job.from_row(row) for row in rows]
        finally:
            conn.close()

    def get_job(self, job_id: int) -> Optional[Job]:
        conn = db.connect(self._db_path)
        try:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return Job.from_row(row) if row else None
        finally:
            conn.close()

    def create_job(
        self,
        name: str,
        description: str = "",
        send_to: str = "",
        program_path: str = "",
        parameters: str = "",
        batch_path: str = "",
        api_enabled: bool = False,
        api_method: str = "",
        api_url: str = "",
        api_headers: str = "",
        api_body: str = "",
        api_auth_type: str = "",
        api_auth_value: str = "",
        api_timeout: int = 0,
        api_retries: int = 0,
        active: bool = True,
        once_per_day: bool = False,
        autostart: bool = False,
        run_as_enabled: bool = False,
        run_as_admin: bool = False,
        run_as_user: str = "",
        run_as_domain: str = "",
        run_as_password: str = "",
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        protected_password = protect_string(run_as_password)
        conn = db.connect(self._db_path)
        try:
            cursor = conn.execute(
                """
                INSERT INTO jobs
                    (name, description, send_to, program_path, parameters, batch_path,
                     api_enabled, api_method, api_url, api_headers, api_body, api_auth_type, api_auth_value,
                     api_timeout, api_retries,
                     active, once_per_day, autostart, run_as_enabled, run_as_admin, run_as_user, run_as_domain,
                     run_as_password, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    description,
                    send_to,
                    program_path,
                    parameters,
                    batch_path,
                    int(api_enabled),
                    api_method,
                    api_url,
                    api_headers,
                    api_body,
                    api_auth_type,
                    api_auth_value,
                    int(api_timeout),
                    int(api_retries),
                    int(active),
                    int(once_per_day),
                    int(autostart),
                    int(run_as_enabled),
                    int(run_as_admin),
                    run_as_user,
                    run_as_domain,
                    protected_password,
                    now,
                    now,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)
        finally:
            conn.close()

    def update_job(
        self,
        job_id: int,
        name: str,
        description: str,
        send_to: str,
        program_path: str,
        parameters: str,
        batch_path: str,
        api_enabled: bool,
        api_method: str,
        api_url: str,
        api_headers: str,
        api_body: str,
        api_auth_type: str,
        api_auth_value: str,
        api_timeout: int,
        api_retries: int,
        active: bool,
        once_per_day: bool,
        autostart: bool,
        run_as_enabled: bool,
        run_as_admin: bool,
        run_as_user: str,
        run_as_domain: str,
        run_as_password: str,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        protected_password = protect_string(run_as_password)
        conn = db.connect(self._db_path)
        try:
            conn.execute(
                """
                UPDATE jobs
                SET name = ?, description = ?, send_to = ?, program_path = ?, parameters = ?,
                    batch_path = ?, api_enabled = ?, api_method = ?, api_url = ?, api_headers = ?, api_body = ?,
                    api_auth_type = ?, api_auth_value = ?, api_timeout = ?, api_retries = ?,
                    active = ?, once_per_day = ?, autostart = ?, run_as_enabled = ?, run_as_admin = ?,
                    run_as_user = ?, run_as_domain = ?, run_as_password = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    name,
                    description,
                    send_to,
                    program_path,
                    parameters,
                    batch_path,
                    int(api_enabled),
                    api_method,
                    api_url,
                    api_headers,
                    api_body,
                    api_auth_type,
                    api_auth_value,
                    int(api_timeout),
                    int(api_retries),
                    int(active),
                    int(once_per_day),
                    int(autostart),
                    int(run_as_enabled),
                    int(run_as_admin),
                    run_as_user,
                    run_as_domain,
                    protected_password,
                    now,
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def delete_job(self, job_id: int) -> None:
        conn = db.connect(self._db_path)
        try:
            conn.execute("DELETE FROM schedules WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM run_logs WHERE job_id = ?", (job_id,))
            conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
        finally:
            conn.close()

    def list_schedule_slots(self, job_id: int) -> list[ScheduleSlot]:
        conn = db.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT * FROM schedules WHERE job_id = ? ORDER BY minute_of_day",
                (job_id,),
            ).fetchall()
            return [ScheduleSlot.from_row(row) for row in rows]
        finally:
            conn.close()

    def replace_schedule_slots(
        self, job_id: int, schedule_type: str, slots: Iterable[int], days_mask: int, date: Optional[str]
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        rows = [
            (
                job_id,
                schedule_type,
                days_mask,
                date,
                minute_of_day,
                1,
                now,
                now,
            )
            for minute_of_day in slots
        ]
        conn = db.connect(self._db_path)
        try:
            conn.execute("DELETE FROM schedules WHERE job_id = ?", (job_id,))
            if rows:
                db.execute_many(
                    conn,
                    """
                    INSERT INTO schedules
                        (job_id, schedule_type, days_mask, date, minute_of_day, active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
            conn.commit()
        finally:
            conn.close()

    def set_schedule_active(self, job_id: int, active: bool) -> None:
        conn = db.connect(self._db_path)
        try:
            conn.execute(
                "UPDATE schedules SET active = ? WHERE job_id = ?",
                (int(active), job_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_run_logs(self, limit: int = 200) -> list[RunLogEntry]:
        conn = db.connect(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT run_logs.job_id,
                       run_logs.scheduled_time,
                       run_logs.status,
                       run_logs.exit_code,
                       jobs.name AS job_name
                FROM run_logs
                LEFT JOIN jobs ON run_logs.job_id = jobs.id
                ORDER BY run_logs.scheduled_time DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [RunLogEntry.from_row(row) for row in rows]
        finally:
            conn.close()

    def get_run_log_details(self, job_id: int, scheduled_time: str) -> str:
        conn = db.connect(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT output, error, start_time, end_time, exit_code
                FROM run_logs
                WHERE job_id = ? AND scheduled_time = ?
                """,
                (job_id, scheduled_time),
            ).fetchone()
            if not row:
                return ""
            output = row["output"] or ""
            error = row["error"] or ""
            header = []
            if row["start_time"]:
                header.append(f"Start: {row['start_time']}")
            if row["end_time"]:
                header.append(f"End: {row['end_time']}")
            if row["exit_code"] is not None:
                header.append(f"Exit: {row['exit_code']}")
            header_text = "\n".join(header)
            body = output + ("\n" if output and error else "") + error
            if header_text and body:
                return header_text + "\n\n" + body
            return header_text or body
        finally:
            conn.close()

    def cleanup_logs(self, days: int = 30) -> int:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="minutes")
        conn = db.connect(self._db_path)
        try:
            cursor = conn.execute(
                "DELETE FROM run_logs WHERE scheduled_time < ?",
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def next_run_for_job(self, job_id: int) -> Optional[datetime]:
        now = datetime.now()
        minute_of_day = now.hour * 60 + now.minute
        today = now.date().isoformat()
        conn = db.connect(self._db_path)
        try:
            row = conn.execute(
                """
                SELECT schedule_type, days_mask, date, minute_of_day
                FROM schedules
                WHERE job_id = ?
                  AND active = 1
                ORDER BY minute_of_day
                """,
                (job_id,),
            ).fetchall()
            if not row:
                return None

            schedule_type = row[0]["schedule_type"]
            if schedule_type == "date":
                return _next_date_run(now, row)
            if schedule_type == "monthly":
                return _next_monthly_run(now, row)
            return _next_recurring_run(now, row)

            return None
        finally:
            conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        conn = db.connect(self._db_path)
        try:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    def set_setting(self, key: str, value: str) -> None:
        conn = db.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            conn.commit()
        finally:
            conn.close()

    def log_api_test(self, job_id: int, status_code: int, response: str, error: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        status = "success" if 200 <= status_code < 300 else "failed"
        conn = db.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO run_logs
                    (job_id, scheduled_time, start_time, end_time, status, exit_code, output, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    now,
                    now,
                    now,
                    status,
                    status_code or None,
                    response or "",
                    error or "",
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _minute_to_datetime(reference: datetime, minute_of_day: int) -> datetime:
    hour = minute_of_day // 60
    minute = minute_of_day % 60
    return reference.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _next_recurring_run(now: datetime, slots) -> Optional[datetime]:
    for day_offset in range(0, 8):
        target = now + timedelta(days=day_offset)
        day_mask = 1 << target.weekday()
        for slot in slots:
            if not (slot["days_mask"] & day_mask):
                continue
            if day_offset == 0 and slot["minute_of_day"] < (now.hour * 60 + now.minute):
                continue
            return _minute_to_datetime(target, slot["minute_of_day"])
    return None


def _next_date_run(now: datetime, slots) -> Optional[datetime]:
    date_str = slots[0]["date"]
    if not date_str:
        return None
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        return None
    if target_date < now.date():
        return None
    for slot in slots:
        if target_date == now.date() and slot["minute_of_day"] < (now.hour * 60 + now.minute):
            continue
        return _minute_to_datetime(datetime.combine(target_date, now.time()), slot["minute_of_day"])
    return None


def _next_monthly_run(now: datetime, slots) -> Optional[datetime]:
    day_str = slots[0]["date"] or ""
    try:
        scheduled_day = int(day_str)
    except ValueError:
        return None
    year = now.year
    month = now.month
    for month_offset in range(0, 13):
        target_month = month + month_offset
        target_year = year + (target_month - 1) // 12
        target_month = (target_month - 1) % 12 + 1
        last_day = calendar.monthrange(target_year, target_month)[1]
        run_day = min(scheduled_day, last_day)
        target_date = datetime(target_year, target_month, run_day)
        if target_date.date() < now.date():
            continue
        for slot in slots:
            if target_date.date() == now.date() and slot["minute_of_day"] < (now.hour * 60 + now.minute):
                continue
            return _minute_to_datetime(target_date, slot["minute_of_day"])
    return None
