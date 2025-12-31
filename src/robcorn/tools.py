from __future__ import annotations

import shutil
import smtplib
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Optional


@dataclass
class ToolResult:
    success: bool
    message: str


class ToolExecutor:
    def copy_path(self, source: Path, destination: Path) -> ToolResult:
        try:
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
            return ToolResult(True, "Copy completed.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def move_path(self, source: Path, destination: Path) -> ToolResult:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            return ToolResult(True, "Move completed.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def delete_path(self, target: Path) -> ToolResult:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return ToolResult(True, "Delete completed.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def zip_path(self, source: Path, zip_target: Path) -> ToolResult:
        try:
            zip_target.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_target, "w", zipfile.ZIP_DEFLATED) as archive:
                if source.is_dir():
                    for item in source.rglob("*"):
                        if item.is_file():
                            archive.write(item, item.relative_to(source))
                else:
                    archive.write(source, source.name)
            return ToolResult(True, "Zip completed.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def download_file(self, url: str, destination: Path) -> ToolResult:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, destination)
            return ToolResult(True, "Download completed.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def send_email(
        self,
        smtp_host: str,
        smtp_port: int,
        sender: str,
        recipient: str,
        subject: str,
        body: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
    ) -> ToolResult:
        try:
            message = EmailMessage()
            message["From"] = sender
            message["To"] = recipient
            message["Subject"] = subject
            message.set_content(body)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                if use_tls:
                    server.starttls()
                if username and password:
                    server.login(username, password)
                server.send_message(message)
            return ToolResult(True, "Email sent.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def set_wallpaper(self, image_path: Path) -> ToolResult:
        try:
            if not image_path.exists():
                return ToolResult(False, "Image path does not exist.")
            # Uses SystemParametersInfo to set the desktop wallpaper on Windows.
            import ctypes

            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                str(image_path),
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE,
            )
            if result == 0:
                return ToolResult(False, "Wallpaper update failed.")
            return ToolResult(True, "Wallpaper updated.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def reboot(self) -> ToolResult:
        try:
            subprocess.run(["shutdown", "/r", "/t", "0"], check=False)
            return ToolResult(True, "Reboot initiated.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def shutdown(self) -> ToolResult:
        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], check=False)
            return ToolResult(True, "Shutdown initiated.")
        except Exception as exc:
            return ToolResult(False, str(exc))

    def connect_vpn(self, command: list[str]) -> ToolResult:
        try:
            subprocess.run(command, check=False)
            return ToolResult(True, "VPN command executed.")
        except Exception as exc:
            return ToolResult(False, str(exc))


def serialize_tool_params(params: dict[str, str]) -> str:
    return ";".join(f"{key}={value}" for key, value in params.items())


def parse_tool_params(raw: str) -> dict[str, str]:
    params: dict[str, str] = {}
    if not raw:
        return params
    for item in raw.split(";"):
        if not item:
            continue
        if "=" not in item:
            params[item] = ""
            continue
        key, value = item.split("=", 1)
        params[key] = value
    return params


def validate_tool_params(tool_name: str, params: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if tool_name in ("copy", "move", "zip"):
        _require_field(params, "source", errors)
        _require_field(params, "destination", errors)
    elif tool_name == "delete":
        _require_field(params, "target", errors)
    elif tool_name == "download":
        _require_field(params, "url", errors)
        _require_field(params, "destination", errors)
    elif tool_name == "email":
        for field in ("smtp_host", "smtp_port", "sender", "recipient", "subject", "body"):
            _require_field(params, field, errors)
    elif tool_name == "wallpaper":
        _require_field(params, "image_path", errors)
    elif tool_name == "vpn":
        _require_field(params, "command", errors)
    return errors


def _require_field(params: dict[str, str], key: str, errors: list[str]) -> None:
    if not params.get(key):
        errors.append(f"Missing {key}.")
