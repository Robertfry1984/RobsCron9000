from __future__ import annotations

from PyQt6.QtCore import Qt
from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..tools import serialize_tool_params


class ToolsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tools")
        self.resize(520, 360)
        self._params: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Tool:"))
        self.tool_combo = QComboBox()
        self.tool_combo.addItems(
            [
                "copy",
                "move",
                "delete",
                "zip",
                "download",
                "email",
                "wallpaper",
                "reboot",
                "shutdown",
                "vpn",
            ]
        )
        header.addWidget(self.tool_combo, 1)
        layout.addLayout(header)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom", "Copy Documents", "Move Logs", "Zip Folder", "Download URL", "Email Alert"])
        preset_row.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_row)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_copy_move_zip("source", "destination"))
        self.stack.addWidget(self._build_copy_move_zip("source", "destination"))
        self.stack.addWidget(self._build_single("target"))
        self.stack.addWidget(self._build_copy_move_zip("source", "destination", destination_mode="file_save"))
        self.stack.addWidget(self._build_download())
        self.stack.addWidget(self._build_email())
        self.stack.addWidget(self._build_single("image_path"))
        self.stack.addWidget(self._build_info("No extra parameters."))
        self.stack.addWidget(self._build_info("No extra parameters."))
        self.stack.addWidget(self._build_single("command"))
        layout.addWidget(self.stack, 1)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.use_button = QPushButton("Use for task")
        self.cancel_button = QPushButton("Cancel")
        button_row.addWidget(self.use_button)
        button_row.addWidget(self.cancel_button)
        layout.addLayout(button_row)

        self.tool_combo.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        self.use_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def selected_tool(self) -> tuple[str, str]:
        tool_name = self.tool_combo.currentText()
        params = self._collect_params_for_tool(tool_name)
        return tool_name, serialize_tool_params(params)

    def accept(self) -> None:
        tool_name = self.tool_combo.currentText()
        params = self._collect_params_for_tool(tool_name)
        missing = [key for key, value in params.items() if value == ""]
        if tool_name in ("reboot", "shutdown"):
            missing = []
        if missing:
            QMessageBox.warning(self, "Tool parameters", "Missing: " + ", ".join(missing))
            return
        if not self._validate_paths(tool_name, params):
            return
        super().accept()

    def _apply_preset(self) -> None:
        preset = self.preset_combo.currentText()
        if preset == "Copy Documents":
            self.tool_combo.setCurrentText("copy")
            self._set_field("source", str(Path.home() / "Documents"))
            self._set_field("destination", str(Path.home() / "Documents" / "Backup"))
        elif preset == "Move Logs":
            self.tool_combo.setCurrentText("move")
            self._set_field("source", str(Path.home() / "logs"))
            self._set_field("destination", str(Path.home() / "Archive" / "logs"))
        elif preset == "Zip Folder":
            self.tool_combo.setCurrentText("zip")
            self._set_field("source", str(Path.home() / "Documents"))
            self._set_field("destination", str(Path.home() / "Documents.zip"))
        elif preset == "Download URL":
            self.tool_combo.setCurrentText("download")
            self._set_field("url", "https://example.com/file.zip")
            self._set_field("destination", str(Path.home() / "Downloads" / "file.zip"))
        elif preset == "Email Alert":
            self.tool_combo.setCurrentText("email")
            self._set_field("smtp_host", "smtp.example.com")
            self._set_field("smtp_port", "587")
            self._set_field("sender", "sender@example.com")
            self._set_field("recipient", "recipient@example.com")
            self._set_field("subject", "RobCron alert")
            self._set_field("body", "Task completed.")
            self._set_field("username", "sender@example.com")
            self._set_field("password", "")

    def _set_field(self, name: str, value: str) -> None:
        line = self.stack.currentWidget().findChild(QLineEdit, name)
        if line:
            line.setText(value)
            return
        text = self.stack.currentWidget().findChild(QTextEdit, name)
        if text:
            text.setPlainText(value)

    def _line_with_browse(self, object_name: str, mode: str) -> QWidget:
        container = QWidget(objectName=object_name)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit()
        line.setObjectName(object_name)
        button = QPushButton("...")
        button.setFixedWidth(32)

        def _browse() -> None:
            if mode == "folder":
                path = QFileDialog.getExistingDirectory(self, "Select Folder")
            else:
                if mode == "file_save":
                    path, _ = QFileDialog.getSaveFileName(self, "Select File")
                else:
                    path, _ = QFileDialog.getOpenFileName(self, "Select File")
            if path:
                line.setText(path)

        button.clicked.connect(_browse)
        layout.addWidget(line, 1)
        layout.addWidget(button)
        return container

    def _validate_paths(self, tool_name: str, params: dict[str, str]) -> bool:
        if tool_name in ("copy", "move", "zip"):
            source = Path(params.get("source", ""))
            if not source.exists():
                QMessageBox.warning(self, "Tool parameters", "Source path does not exist.")
                return False
        if tool_name == "delete":
            target = Path(params.get("target", ""))
            if not target.exists():
                QMessageBox.warning(self, "Tool parameters", "Target path does not exist.")
                return False
        if tool_name == "wallpaper":
            image_path = Path(params.get("image_path", ""))
            if not image_path.exists():
                QMessageBox.warning(self, "Tool parameters", "Image path does not exist.")
                return False
        if tool_name == "email":
            smtp_port = params.get("smtp_port", "")
            if smtp_port and not smtp_port.isdigit():
                QMessageBox.warning(self, "Tool parameters", "SMTP port must be numeric.")
                return False
        return True

    def _collect_params_for_tool(self, tool_name: str) -> dict[str, str]:
        if tool_name in ("copy", "move", "zip"):
            return {
                "source": self._get_field("source"),
                "destination": self._get_field("destination"),
            }
        if tool_name == "delete":
            return {"target": self._get_field("target")}
        if tool_name == "download":
            return {
                "url": self._get_field("url"),
                "destination": self._get_field("destination"),
            }
        if tool_name == "vpn":
            return {"command": self._get_field("command")}
        if tool_name == "email":
            return {
                "smtp_host": self._get_field("smtp_host"),
                "smtp_port": self._get_field("smtp_port"),
                "sender": self._get_field("sender"),
                "recipient": self._get_field("recipient"),
                "subject": self._get_field("subject"),
                "body": self._get_field("body"),
                "username": self._get_field("username"),
                "password": self._get_field("password"),
                "use_tls": "true" if self._get_checkbox("use_tls") else "false",
            }
        if tool_name == "wallpaper":
            return {"image_path": self._get_field("image_path")}
        if tool_name in ("reboot", "shutdown"):
            return {}
        return {}

    def _build_copy_move_zip(self, label_a: str, label_b: str, destination_mode: str = "folder") -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow(label_a.capitalize() + ":", self._line_with_browse(label_a, mode="folder"))
        form.addRow(label_b.capitalize() + ":", self._line_with_browse(label_b, mode=destination_mode))
        return widget

    def _build_single(self, label: str) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        if label == "command":
            form.addRow(label.capitalize() + ":", QLineEdit(objectName=label))
        else:
            form.addRow(label.capitalize() + ":", self._line_with_browse(label, mode="file_open"))
        return widget

    def _build_download(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("URL:", QLineEdit(objectName="url"))
        form.addRow("Destination:", self._line_with_browse("destination", mode="file_save"))
        return widget

    def _build_email(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow("SMTP Host:", QLineEdit(objectName="smtp_host"))
        form.addRow("SMTP Port:", QLineEdit(objectName="smtp_port"))
        form.addRow("Sender:", QLineEdit(objectName="sender"))
        form.addRow("Recipient:", QLineEdit(objectName="recipient"))
        form.addRow("Subject:", QLineEdit(objectName="subject"))
        body = QTextEdit(objectName="body")
        body.setFixedHeight(80)
        form.addRow("Body:", body)
        form.addRow("Username:", QLineEdit(objectName="username"))
        password = QLineEdit(objectName="password")
        password.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", password)
        tls = QCheckBox("Use TLS")
        tls.setChecked(True)
        tls.setObjectName("use_tls")
        form.addRow("", tls)
        return widget

    def _build_info(self, text: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label, 1)
        return widget

    def _get_field(self, name: str) -> str:
        container = self.stack.currentWidget()
        line = container.findChild(QLineEdit, name)
        if line:
            return line.text().strip()
        text = container.findChild(QTextEdit, name)
        if text:
            return text.toPlainText().strip()
        return ""

    def _get_checkbox(self, name: str) -> bool:
        widget = self.stack.currentWidget().findChild(QCheckBox, name)
        return bool(widget and widget.isChecked())
