from __future__ import annotations

import json

from typing import Callable, Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from ..schedule_api import perform_request

class ApiRequestDialog(QDialog):
    def __init__(
        self,
        method: str = "",
        url: str = "",
        headers: str = "",
        body: str = "",
        auth_type: str = "",
        auth_value: str = "",
        timeout: int = 0,
        retries: int = 0,
        log_callback: Optional[Callable[[dict], None]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("API Request")
        self.resize(560, 480)
        self._log_callback = log_callback
        self._build_ui(method, url, headers, body, auth_type, auth_value, timeout, retries)

    def _build_ui(
        self,
        method: str,
        url: str,
        headers: str,
        body: str,
        auth_type: str,
        auth_value: str,
        timeout: int,
        retries: int,
    ) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE", "PATCH"])
        if method:
            self.method_combo.setCurrentText(method.upper())
        self.url_input = QLineEdit()
        self.url_input.setText(url)
        self.headers_input = QTextEdit()
        self.headers_input.setPlaceholderText("Header: Value")
        self.headers_input.setText(headers)
        self.body_input = QTextEdit()
        self.body_input.setPlaceholderText("{\"key\":\"value\"}")
        self.body_input.setText(body)
        self.auth_combo = QComboBox()
        self.auth_combo.addItems(["None", "Bearer", "Basic"])
        if auth_type:
            self.auth_combo.setCurrentText(auth_type)
        self.auth_input = QLineEdit()
        self.auth_input.setPlaceholderText("Bearer token or user:password")
        self.auth_input.setText(auth_value)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 300)
        self.timeout_spin.setValue(timeout)
        self.retries_spin = QSpinBox()
        self.retries_spin.setRange(0, 10)
        self.retries_spin.setValue(retries)
        form.addRow(QLabel("Method:"), self.method_combo)
        form.addRow(QLabel("URL:"), self.url_input)
        form.addRow(QLabel("Headers:"), self.headers_input)
        form.addRow(QLabel("Body (JSON):"), self.body_input)
        form.addRow(QLabel("Auth:"), self.auth_combo)
        form.addRow(QLabel("Auth value:"), self.auth_input)
        form.addRow(QLabel("Timeout (sec):"), self.timeout_spin)
        form.addRow(QLabel("Retries:"), self.retries_spin)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.test_button = QPushButton("Test Request")
        self.save_button = QPushButton("Save")
        self.test_button.clicked.connect(self._test_request)
        self.save_button.clicked.connect(self.accept)
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.save_button)
        layout.addLayout(buttons)

    def accept(self) -> None:
        if self.body_input.toPlainText().strip():
            try:
                json.loads(self.body_input.toPlainText())
            except json.JSONDecodeError:
                QMessageBox.warning(self, "API Request", "Body is not valid JSON.")
                return
        super().accept()

    def get_values(self) -> tuple[str, str, str, str, str, str, int, int]:
        return (
            self.method_combo.currentText().strip(),
            self.url_input.text().strip(),
            self.headers_input.toPlainText().strip(),
            self.body_input.toPlainText().strip(),
            self.auth_combo.currentText().strip(),
            self.auth_input.text().strip(),
            int(self.timeout_spin.value()),
            int(self.retries_spin.value()),
        )

    def _test_request(self) -> None:
        method, url, headers, body, auth_type, auth_value, timeout, retries = self.get_values()
        if not url or not method:
            QMessageBox.warning(self, "API Request", "Method and URL are required to test.")
            return
        result = perform_request(
            method=method,
            url=url,
            headers=_parse_headers(headers),
            body=body,
            auth_type=auth_type,
            auth_value=auth_value,
            timeout=timeout,
            retries=retries,
        )
        if self._log_callback:
            self._log_callback(result)
        status = result.get("status", 0)
        response = result.get("response", "")
        error = result.get("error", "")
        QMessageBox.information(
            self,
            "Test Result",
            f"Status: {status}\nError: {error}\n\nResponse:\n{response}",
        )


def _parse_headers(raw: str) -> dict[str, str]:
    headers = {}
    for line in raw.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers
