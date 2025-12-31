from __future__ import annotations

import calendar
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from . import db
from .models import Job
from .runner import JobRunner


@dataclass(frozen=True)
class DueJob:
    job: Job
    schedule_id: int
    scheduled_time: datetime


class SchedulerEngine:
    def __init__(
        self,
        db_path: Path,
        runner: Optional[JobRunner] = None,
        poll_interval_seconds: float = 1.0,
        max_workers: int = 4,
    ):
        self._db_path = db_path
        self._runner = runner or JobRunner(db_path)
        self._poll_interval = poll_interval_seconds
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_checked_minute: Optional[str] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def ensure_running(self) -> None:
        if not self._thread or not self._thread.is_alive():
            self.start()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._executor.shutdown(wait=False)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                now = datetime.now()
                minute_key = now.strftime("%Y-%m-%d %H:%M")
                if minute_key != self._last_checked_minute:
                    self._last_checked_minute = minute_key
                    for due_job in self._get_due_jobs(now):
                        self._executor.submit(self._run_and_persist, due_job)
            except Exception:
                logging.exception("Scheduler loop failure")
            time.sleep(self._poll_interval)

    def _get_due_jobs(self, now: datetime) -> Iterable[DueJob]:
        minute_of_day = now.hour * 60 + now.minute
        day_mask = weekday_mask(now)
        today = now.date().isoformat()
        day_str = f"{now.day:02d}"
        last_day = calendar.monthrange(now.year, now.month)[1]
        scheduled_time = now.replace(second=0, microsecond=0)

        conn = db.connect(self._db_path)
        try:
            rows = conn.execute(
                """
                SELECT j.*, s.id AS schedule_id, s.schedule_type, s.days_mask, s.date, s.minute_of_day
                FROM schedules s
                JOIN jobs j ON s.job_id = j.id
                WHERE j.active = 1
                  AND s.active = 1
                  AND s.minute_of_day = ?
                  AND (
                        (s.schedule_type = 'recurring' AND (s.days_mask & ?) != 0)
                        OR (s.schedule_type = 'date' AND s.date = ?)
                        OR (s.schedule_type = 'monthly' AND s.date = ?)
                      )
                """,
                (minute_of_day, day_mask, today, day_str),
            ).fetchall()

            due_jobs = []
            for row in rows:
                job = Job.from_row(row)
                if job.once_per_day and job.last_run_at:
                    if job.last_run_at.date().isoformat() == today:
                        continue
                if self._has_run_log(conn, job.id, scheduled_time):
                    continue
                if row["schedule_type"] == "monthly":
                    try:
                        scheduled_day = int(row["date"] or "0")
                    except ValueError:
                        continue
                    if scheduled_day > last_day and now.day != last_day:
                        continue
                due_jobs.append(
                    DueJob(
                        job=job,
                        schedule_id=row["schedule_id"],
                        scheduled_time=scheduled_time,
                    )
                )
            return due_jobs
        finally:
            conn.close()

    def _has_run_log(self, conn, job_id: int, scheduled_time: datetime) -> bool:
        row = conn.execute(
            """
            SELECT 1 FROM run_logs
            WHERE job_id = ? AND scheduled_time = ?
            """,
            (job_id, scheduled_time.isoformat(timespec="minutes")),
        ).fetchone()
        return row is not None

    def _run_and_persist(self, due_job: DueJob) -> None:
        result = self._runner.run_job(due_job.job, due_job.scheduled_time)
        self._runner.persist_run(due_job.job.id, due_job.scheduled_time, result)


def weekday_mask(dt: datetime) -> int:
    return 1 << dt.weekday()
