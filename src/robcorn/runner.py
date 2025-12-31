from __future__ import annotations

import ctypes
import platform
import shlex
import subprocess
import tempfile
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from . import db
from .models import Job
from .schedule_api import perform_request
from .tools import ToolExecutor, parse_tool_params, validate_tool_params


@dataclass
class RunResult:
    status: str
    exit_code: Optional[int]
    output: str
    error: str
    start_time: datetime
    end_time: datetime


class JobRunner:
    def __init__(self, db_path: Path, default_timeout_seconds: int = 3600):
        self._db_path = db_path
        self._default_timeout = default_timeout_seconds

    def run_job(self, job: Job, scheduled_time: datetime) -> RunResult:
        start_time = datetime.now()
        if job.api_enabled and job.api_url and job.api_method:
            return self._run_api(job, start_time)
        if job.program_path.startswith("tool:"):
            return self._run_tool(job, start_time)
        command = self._build_command(job)
        if not command:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error="No executable or batch file configured.",
                start_time=start_time,
                end_time=end_time,
            )

        if job.run_as_admin:
            return self._run_as_admin(command, start_time)
        if job.run_as_enabled and job.run_as_user and job.run_as_password:
            return self._run_as(job, command, start_time)

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self._default_timeout,
                shell=False,
            )
            end_time = datetime.now()
            return RunResult(
                status="success" if completed.returncode == 0 else "failed",
                exit_code=completed.returncode,
                output=completed.stdout or "",
                error=completed.stderr or "",
                start_time=start_time,
                end_time=end_time,
            )
        except subprocess.TimeoutExpired as exc:
            end_time = datetime.now()
            return RunResult(
                status="timeout",
                exit_code=None,
                output=exc.stdout or "",
                error=exc.stderr or "Process timed out.",
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error=str(exc),
                start_time=start_time,
                end_time=end_time,
            )

    def persist_run(self, job_id: int, scheduled_time: datetime, result: RunResult) -> None:
        conn = db.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_logs
                    (job_id, scheduled_time, start_time, end_time, status, exit_code, output, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    scheduled_time.isoformat(timespec="minutes"),
                    result.start_time.isoformat(timespec="seconds"),
                    result.end_time.isoformat(timespec="seconds"),
                    result.status,
                    result.exit_code,
                    result.output,
                    result.error,
                ),
            )
            conn.execute(
                "UPDATE jobs SET last_run_at = ?, updated_at = ? WHERE id = ?",
                (
                    result.end_time.isoformat(timespec="seconds"),
                    result.end_time.isoformat(timespec="seconds"),
                    job_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _build_command(self, job: Job) -> Optional[Sequence[str]]:
        if job.program_path.startswith("tool:"):
            return None
        if job.batch_path:
            batch_path = Path(job.batch_path)
            if not batch_path.exists():
                return None
            return ["cmd.exe", "/c", str(batch_path)]
        if job.program_path:
            program_path = Path(job.program_path)
            if not program_path.exists():
                return None
            args = [str(program_path)]
            if job.parameters:
                args.extend(_split_params(job.parameters))
            return args
        return None

    def _run_api(self, job: Job, start_time: datetime) -> RunResult:
        headers = _parse_headers(job.api_headers)
        result = perform_request(
            method=job.api_method,
            url=job.api_url,
            headers=headers,
            body=job.api_body,
            auth_type=job.api_auth_type,
            auth_value=job.api_auth_value,
            timeout=job.api_timeout,
            retries=job.api_retries,
        )
        end_time = datetime.now()
        status_code = int(result.get("status", 0) or 0)
        ok = 200 <= status_code < 300
        return RunResult(
            status="success" if ok else "failed",
            exit_code=status_code if status_code else None,
            output=result.get("response", ""),
            error=result.get("error", ""),
            start_time=start_time,
            end_time=end_time,
        )

    def _run_as(self, job: Job, command: Sequence[str], start_time: datetime) -> RunResult:
        if platform.system().lower() != "windows":
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error="Run-as is only supported on Windows.",
                start_time=start_time,
                end_time=end_time,
            )

        output_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as handle:
                output_path = Path(handle.name)
            base_command = _command_line(command)
            wrapped = f'cmd.exe /c "{base_command} 1> "{output_path}" 2>&1"'
            exit_code = _create_process_with_logon(
                username=job.run_as_user,
                domain=job.run_as_domain,
                password=job.run_as_password,
                command=wrapped,
            )
            end_time = datetime.now()
            output = ""
            if output_path and output_path.exists():
                output = output_path.read_text(errors="replace")
            return RunResult(
                status="success" if exit_code == 0 else "failed",
                exit_code=exit_code,
                output=output,
                error="",
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error=str(exc),
                start_time=start_time,
                end_time=end_time,
            )
        finally:
            if output_path and output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass

    def _run_as_admin(self, command: Sequence[str], start_time: datetime) -> RunResult:
        try:
            exit_code = _shell_execute_admin(command)
            end_time = datetime.now()
            return RunResult(
                status="success" if exit_code == 0 else "failed",
                exit_code=exit_code,
                output="",
                error="",
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error=str(exc),
                start_time=start_time,
                end_time=end_time,
            )

    def _run_tool(self, job: Job, start_time: datetime) -> RunResult:
        tool_name = job.program_path.split("tool:", 1)[-1]
        params = parse_tool_params(job.parameters)
        errors = validate_tool_params(tool_name, params)
        if errors:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=1,
                output="",
                error=" ".join(errors),
                start_time=start_time,
                end_time=end_time,
            )
        executor = ToolExecutor()
        try:
            result = _execute_tool(executor, tool_name, params)
            end_time = datetime.now()
            return RunResult(
                status="success" if result.success else "failed",
                exit_code=0 if result.success else 1,
                output=result.message if result.success else "",
                error="" if result.success else result.message,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as exc:
            end_time = datetime.now()
            return RunResult(
                status="failed",
                exit_code=None,
                output="",
                error=str(exc),
                start_time=start_time,
                end_time=end_time,
            )


def _execute_tool(executor: ToolExecutor, tool_name: str, params: dict[str, str]):
    if tool_name == "copy":
        return executor.copy_path(Path(params["source"]), Path(params["destination"]))
    if tool_name == "move":
        return executor.move_path(Path(params["source"]), Path(params["destination"]))
    if tool_name == "delete":
        return executor.delete_path(Path(params["target"]))
    if tool_name == "zip":
        return executor.zip_path(Path(params["source"]), Path(params["destination"]))
    if tool_name == "download":
        return executor.download_file(params["url"], Path(params["destination"]))
    if tool_name == "email":
        return executor.send_email(
            smtp_host=params.get("smtp_host", ""),
            smtp_port=int(params.get("smtp_port", "25") or 25),
            sender=params.get("sender", ""),
            recipient=params.get("recipient", ""),
            subject=params.get("subject", ""),
            body=params.get("body", ""),
            username=params.get("username", "") or None,
            password=params.get("password", "") or None,
            use_tls=params.get("use_tls", "true").lower() != "false",
        )
    if tool_name == "wallpaper":
        return executor.set_wallpaper(Path(params["image_path"]))
    if tool_name == "reboot":
        return executor.reboot()
    if tool_name == "shutdown":
        return executor.shutdown()
    if tool_name == "vpn":
        command = params.get("command", "").split(" ")
        return executor.connect_vpn([part for part in command if part])
    raise ValueError(f"Unknown tool: {tool_name}")


def _create_process_with_logon(username: str, domain: str, password: str, command) -> int:
    import ctypes
    from ctypes import wintypes

    LOGON_WITH_PROFILE = 0x00000001
    CREATE_NO_WINDOW = 0x08000000
    INFINITE = 0xFFFFFFFF

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    if isinstance(command, str):
        command_line = command
    else:
        command_line = _command_line(command)
    startup_info = STARTUPINFO()
    startup_info.cb = ctypes.sizeof(startup_info)
    process_info = PROCESS_INFORMATION()
    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    if not advapi32.CreateProcessWithLogonW(
        username,
        domain or None,
        password,
        LOGON_WITH_PROFILE,
        None,
        command_line,
        CREATE_NO_WINDOW,
        None,
        None,
        ctypes.byref(startup_info),
        ctypes.byref(process_info),
    ):
        error = ctypes.get_last_error()
        raise OSError(f"CreateProcessWithLogonW failed: {error}")

    kernel32.WaitForSingleObject(process_info.hProcess, INFINITE)
    exit_code = wintypes.DWORD()
    kernel32.GetExitCodeProcess(process_info.hProcess, ctypes.byref(exit_code))
    kernel32.CloseHandle(process_info.hProcess)
    kernel32.CloseHandle(process_info.hThread)
    return int(exit_code.value)


def _command_line(command: Sequence[str]) -> str:
    return " ".join(f'"{arg}"' if " " in arg else arg for arg in command)


def _shell_execute_admin(command: Sequence[str]) -> int:
    if not command:
        return 1
    file_path = command[0]
    params = " ".join(f'"{arg}"' if " " in arg else arg for arg in command[1:])
    SEE_MASK_NOCLOSEPROCESS = 0x00000040

    class SHELLEXECUTEINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("fMask", wintypes.ULONG),
            ("hwnd", wintypes.HWND),
            ("lpVerb", wintypes.LPCWSTR),
            ("lpFile", wintypes.LPCWSTR),
            ("lpParameters", wintypes.LPCWSTR),
            ("lpDirectory", wintypes.LPCWSTR),
            ("nShow", ctypes.c_int),
            ("hInstApp", wintypes.HINSTANCE),
            ("lpIDList", wintypes.LPVOID),
            ("lpClass", wintypes.LPCWSTR),
            ("hkeyClass", wintypes.HKEY),
            ("dwHotKey", wintypes.DWORD),
            ("hIcon", wintypes.HANDLE),
            ("hProcess", wintypes.HANDLE),
        ]

    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.hwnd = None
    sei.lpVerb = "runas"
    sei.lpFile = file_path
    sei.lpParameters = params
    sei.lpDirectory = None
    sei.nShow = 1
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        raise OSError("ShellExecuteExW failed")
    ctypes.windll.kernel32.WaitForSingleObject(sei.hProcess, 0xFFFFFFFF)
    exit_code = wintypes.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code))
    ctypes.windll.kernel32.CloseHandle(sei.hProcess)
    return int(exit_code.value)


def _split_params(params: str) -> list[str]:
    if not params:
        return []
    return shlex.split(params, posix=False)


def _parse_headers(raw: str) -> dict[str, str]:
    if not raw:
        return {}
    headers = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers
