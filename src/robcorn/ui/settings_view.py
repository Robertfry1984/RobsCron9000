from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..repository import Repository
from ..windows import (
    install_service,
    query_service_status,
    remove_service,
    set_autostart,
    start_service,
    stop_service,
)


class SettingsView(QWidget):
    def __init__(self, repository: Repository):
        super().__init__()
        self._repository = repository
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.autostart_checkbox = QCheckBox("Start scheduler with Windows")
        self.service_checkbox = QCheckBox("Run scheduler as service (admin)")
        self.exec_path_input = QLineEdit()
        form.addRow(self.autostart_checkbox)
        form.addRow("Scheduler executable:", self.exec_path_input)
        form.addRow(self.service_checkbox)
        layout.addLayout(form)
        self.save_button = QPushButton("Apply")
        layout.addWidget(self.save_button)
        self.service_install = QPushButton("Install Service")
        self.service_remove = QPushButton("Remove Service")
        self.service_start = QPushButton("Start Service")
        self.service_stop = QPushButton("Stop Service")
        self.service_status = QLabel("Service status: unknown")
        layout.addWidget(self.service_install)
        layout.addWidget(self.service_remove)
        layout.addWidget(self.service_start)
        layout.addWidget(self.service_stop)
        layout.addWidget(self.service_status)
        layout.addWidget(QLabel("Service setup requires administrator privileges."))
        layout.addStretch(1)

        self.save_button.clicked.connect(self._save)
        self.service_install.clicked.connect(self._install_service)
        self.service_remove.clicked.connect(self._remove_service)
        self.service_start.clicked.connect(self._start_service)
        self.service_stop.clicked.connect(self._stop_service)

    def _load(self) -> None:
        autostart = self._repository.get_setting("autostart_enabled", "0") == "1"
        service = self._repository.get_setting("service_enabled", "0") == "1"
        exec_path = self._repository.get_setting("autostart_path", sys.executable)
        self.autostart_checkbox.setChecked(autostart)
        self.service_checkbox.setChecked(service)
        self.exec_path_input.setText(exec_path)
        self._refresh_service_status()

    def _save(self) -> None:
        autostart = self.autostart_checkbox.isChecked()
        service = self.service_checkbox.isChecked()
        exec_path = self.exec_path_input.text().strip() or sys.executable
        self._repository.set_setting("autostart_enabled", "1" if autostart else "0")
        self._repository.set_setting("service_enabled", "1" if service else "0")
        self._repository.set_setting("autostart_path", exec_path)
        set_autostart("RobCron", Path(exec_path), autostart)
        self._refresh_service_status()

    def _install_service(self) -> None:
        exec_path = self.exec_path_input.text().strip() or sys.executable
        if exec_path.lower().endswith(".exe") and "python" not in exec_path.lower():
            command = f"\"{exec_path}\" --service"
        else:
            command = f"\"{exec_path}\" -m robcorn.service_main"
        code, output = install_service("RobCron", "RobCron Scheduler", command)
        self._handle_service_result(code, output, "install")
        self._refresh_service_status()

    def _remove_service(self) -> None:
        code, output = remove_service("RobCron")
        self._handle_service_result(code, output, "remove")
        self._refresh_service_status()

    def _start_service(self) -> None:
        code, output = start_service("RobCron")
        self._handle_service_result(code, output, "start")
        self._refresh_service_status()

    def _stop_service(self) -> None:
        code, output = stop_service("RobCron")
        self._handle_service_result(code, output, "stop")
        self._refresh_service_status()

    def _refresh_service_status(self) -> None:
        status = query_service_status("RobCron")
        self.service_status.setText(f"Service status: {status}")

    def _handle_service_result(self, code: int, output: str, action: str) -> None:
        if code == 0:
            return
        message = output.strip() or f"Service {action} failed."
        if "ACCESS_DENIED" in message.upper() or "Access is denied" in message:
            message += "\nRun as Administrator."
        QMessageBox.warning(self, "Service", message)
