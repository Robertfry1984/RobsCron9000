from __future__ import annotations

import base64
import subprocess
import ctypes
from pathlib import Path
from typing import Optional

import winreg
from ctypes import wintypes


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def set_autostart(app_name: str, executable_path: Path, enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, str(executable_path))
        else:
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                pass


def create_shortcut(
    shortcut_path: Path,
    target_path: Path,
    arguments: Optional[str] = None,
    working_dir: Optional[Path] = None,
    icon_path: Optional[Path] = None,
) -> None:
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)
    args = arguments or ""
    workdir = str(working_dir) if working_dir else ""
    icon = str(icon_path) if icon_path else ""
    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$Shortcut.TargetPath = '{target_path}'; "
        f"$Shortcut.Arguments = '{args}'; "
        f"$Shortcut.WorkingDirectory = '{workdir}'; "
        f"$Shortcut.IconLocation = '{icon}'; "
        "$Shortcut.Save();"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=False)


def install_service(service_name: str, display_name: str, command: str) -> tuple[int, str]:
    result = subprocess.run(
        [
            "sc",
            "create",
            service_name,
            f"binPath= {command}",
            "start= auto",
            f"DisplayName= {display_name}",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or result.stderr or "")


def remove_service(service_name: str) -> tuple[int, str]:
    result = subprocess.run(
        ["sc", "delete", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or result.stderr or "")


def start_service(service_name: str) -> tuple[int, str]:
    result = subprocess.run(
        ["sc", "start", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or result.stderr or "")


def stop_service(service_name: str) -> tuple[int, str]:
    result = subprocess.run(
        ["sc", "stop", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or result.stderr or "")


def query_service_status(service_name: str) -> str:
    result = subprocess.run(
        ["sc", "query", service_name],
        check=False,
        capture_output=True,
        text=True,
    )
    output = result.stdout or ""
    for line in output.splitlines():
        if "STATE" in line:
            return line.split(":")[-1].strip()
    return "UNKNOWN"


def protect_string(value: str) -> str:
    if not value:
        return ""
    if value.startswith("enc:"):
        return value
    data = value.encode("utf-8")
    blob_in = _data_blob(data)
    blob_out = _data_blob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        return value
    try:
        encrypted = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        return "enc:" + base64.b64encode(encrypted).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def unprotect_string(value: str) -> str:
    if not value or not value.startswith("enc:"):
        return value
    raw = base64.b64decode(value[4:])
    blob_in = _data_blob(raw)
    blob_out = _data_blob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        return value
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData).decode("utf-8", errors="replace")
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _data_blob(data: bytes = b""):
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_byte)),
        ]

    blob = DATA_BLOB()
    if data:
        blob.cbData = len(data)
        blob.pbData = ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_byte))
    return blob
