from __future__ import annotations

import json
import socket
import subprocess
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
import traceback

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from robcorn.config import db_path  # noqa: E402
from robcorn.env import get_env  # noqa: E402
from robcorn.repository import Repository  # noqa: E402


PORT = int(get_env("ROBCORN_API_PORT", "11349") or "11349")


def _log_exception(exc: Exception) -> None:
    log_path = Path(__file__).resolve().parent / "server.log"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now().isoformat()} {type(exc).__name__}: {exc}\n")
        handle.write(traceback.format_exc())
        handle.write("\n")


def _kill_process_on_port(port: int) -> None:
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = result.stdout.splitlines()
        pids = set()
        for line in lines:
            if f":{port} " in line and "LISTENING" in line:
                parts = line.split()
                if parts:
                    pids.add(parts[-1])
        for pid in pids:
            subprocess.run(["taskkill", "/F", "/PID", pid], check=False)
    except Exception:
        pass


class TaskAPIHandler(BaseHTTPRequestHandler):
    repo = Repository(db_path())

    def _json_response(self, status: int, payload: Any) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:
        try:
            if self.path.rstrip("/") == "/tasks":
                tasks = []
                for job in self.repo.list_jobs():
                    slots = self.repo.list_schedule_slots(job.id)
                    schedules = [
                        {
                            "schedule_type": slot.schedule_type,
                            "days_mask": slot.days_mask,
                            "date": slot.date,
                            "minute_of_day": slot.minute_of_day,
                            "active": slot.active,
                        }
                        for slot in slots
                    ]
                    tasks.append(
                        {
                            "id": job.id,
                            "name": job.name,
                            "description": job.description,
                            "send_to": job.send_to,
                            "program_path": job.program_path,
                            "parameters": job.parameters,
                            "batch_path": job.batch_path,
                            "api_enabled": job.api_enabled,
                            "api_method": job.api_method,
                            "api_url": job.api_url,
                            "api_headers": job.api_headers,
                            "api_body": job.api_body,
                            "api_auth_type": job.api_auth_type,
                            "api_auth_value": job.api_auth_value,
                            "api_timeout": job.api_timeout,
                            "api_retries": job.api_retries,
                            "active": job.active,
                            "once_per_day": job.once_per_day,
                            "autostart": job.autostart,
                            "run_as_enabled": job.run_as_enabled,
                            "run_as_admin": job.run_as_admin,
                            "schedules": schedules,
                        }
                    )
                self._json_response(200, {"tasks": tasks})
                return
            self._json_response(404, {"error": "Not found"})
        except Exception as exc:
            _log_exception(exc)
            self._json_response(500, {"error": str(exc)})

    def do_POST(self) -> None:
        try:
            if self.path.rstrip("/") == "/tasks":
                data = self._read_json()
                job_id = self.repo.create_job(
                    name=data.get("name", "New Job"),
                    description=data.get("description", ""),
                    send_to=data.get("send_to", ""),
                    program_path=data.get("program_path", ""),
                    parameters=data.get("parameters", ""),
                    batch_path=data.get("batch_path", ""),
                    api_enabled=bool(data.get("api_enabled", False)),
                    api_method=data.get("api_method", ""),
                    api_url=data.get("api_url", ""),
                    api_headers=data.get("api_headers", ""),
                    api_body=data.get("api_body", ""),
                    api_auth_type=data.get("api_auth_type", ""),
                    api_auth_value=data.get("api_auth_value", ""),
                    api_timeout=int(data.get("api_timeout", 0) or 0),
                    api_retries=int(data.get("api_retries", 0) or 0),
                    active=bool(data.get("active", True)),
                    once_per_day=bool(data.get("once_per_day", False)),
                    autostart=bool(data.get("autostart", False)),
                    run_as_enabled=bool(data.get("run_as_enabled", False)),
                    run_as_admin=bool(data.get("run_as_admin", False)),
                    run_as_user=data.get("run_as_user", ""),
                    run_as_domain=data.get("run_as_domain", ""),
                    run_as_password=data.get("run_as_password", ""),
                )
                schedules = data.get("schedules", [])
                if schedules:
                    schedule_type = schedules[0].get("schedule_type", "recurring")
                    days_mask = int(schedules[0].get("days_mask", 0))
                    date = schedules[0].get("date")
                    slots = [int(item.get("minute_of_day")) for item in schedules]
                    self.repo.replace_schedule_slots(job_id, schedule_type, slots, days_mask, date)
                    self.repo.set_schedule_active(job_id, bool(schedules[0].get("active", True)))
                self._json_response(201, {"id": job_id})
                return
            self._json_response(404, {"error": "Not found"})
        except Exception as exc:
            _log_exception(exc)
            self._json_response(500, {"error": str(exc)})

    def do_PUT(self) -> None:
        try:
            if self.path.startswith("/tasks/"):
                job_id = int(self.path.split("/")[-1])
                job = self.repo.get_job(job_id)
                if not job:
                    self._json_response(404, {"error": "Job not found"})
                    return
                data = self._read_json()
                self.repo.update_job(
                    job_id=job_id,
                    name=data.get("name", job.name),
                    description=data.get("description", job.description),
                    send_to=data.get("send_to", job.send_to),
                    program_path=data.get("program_path", job.program_path),
                    parameters=data.get("parameters", job.parameters),
                    batch_path=data.get("batch_path", job.batch_path),
                    api_enabled=bool(data.get("api_enabled", job.api_enabled)),
                    api_method=data.get("api_method", job.api_method),
                    api_url=data.get("api_url", job.api_url),
                    api_headers=data.get("api_headers", job.api_headers),
                    api_body=data.get("api_body", job.api_body),
                    api_auth_type=data.get("api_auth_type", job.api_auth_type),
                    api_auth_value=data.get("api_auth_value", job.api_auth_value),
                    api_timeout=int(data.get("api_timeout", job.api_timeout) or 0),
                    api_retries=int(data.get("api_retries", job.api_retries) or 0),
                    active=bool(data.get("active", job.active)),
                    once_per_day=bool(data.get("once_per_day", job.once_per_day)),
                    autostart=bool(data.get("autostart", job.autostart)),
                    run_as_enabled=bool(data.get("run_as_enabled", job.run_as_enabled)),
                    run_as_admin=bool(data.get("run_as_admin", job.run_as_admin)),
                    run_as_user=data.get("run_as_user", job.run_as_user),
                    run_as_domain=data.get("run_as_domain", job.run_as_domain),
                    run_as_password=data.get("run_as_password", job.run_as_password),
                )
                schedules = data.get("schedules")
                if schedules is not None:
                    if schedules:
                        schedule_type = schedules[0].get("schedule_type", "recurring")
                        days_mask = int(schedules[0].get("days_mask", 0))
                        date = schedules[0].get("date")
                        slots = [int(item.get("minute_of_day")) for item in schedules]
                        self.repo.replace_schedule_slots(job_id, schedule_type, slots, days_mask, date)
                        self.repo.set_schedule_active(job_id, bool(schedules[0].get("active", True)))
                    else:
                        self.repo.replace_schedule_slots(job_id, "recurring", [], 0, None)
                self._json_response(200, {"status": "updated"})
                return
            self._json_response(404, {"error": "Not found"})
        except Exception as exc:
            _log_exception(exc)
            self._json_response(500, {"error": str(exc)})

    def do_DELETE(self) -> None:
        try:
            if self.path.startswith("/tasks/"):
                job_id = int(self.path.split("/")[-1])
                self.repo.delete_job(job_id)
                self._json_response(200, {"status": "deleted"})
                return
            self._json_response(404, {"error": "Not found"})
        except Exception as exc:
            _log_exception(exc)
            self._json_response(500, {"error": str(exc)})

    def log_message(self, format, *args):
        return


def _bind_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", PORT), TaskAPIHandler)
    TaskAPIHandler.repo.init()
    return server


def main() -> None:
    try:
        server = _bind_server()
    except OSError:
        _kill_process_on_port(PORT)
        server = _bind_server()
    server.serve_forever()


if __name__ == "__main__":
    main()
