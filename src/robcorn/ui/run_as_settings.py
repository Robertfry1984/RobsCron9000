from __future__ import annotations

from PyQt6.QtWidgets import QCheckBox, QGridLayout, QLabel, QLineEdit, QWidget


class RunAsSettings(QWidget):
    def __init__(self):
        super().__init__()
        layout = QGridLayout(self)
        self.admin_checkbox = QCheckBox("Run as administrator")
        self.admin_checkbox.setChecked(False)
        layout.addWidget(self.admin_checkbox, 0, 0, 1, 2)
        layout.addWidget(QLabel("User:"), 1, 0)
        self.user_input = QLineEdit()
        layout.addWidget(self.user_input, 1, 1)
        layout.addWidget(QLabel("Domain:"), 2, 0)
        self.domain_input = QLineEdit()
        layout.addWidget(self.domain_input, 2, 1)
        layout.addWidget(QLabel("Password:"), 3, 0)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input, 3, 1)

    def set_credentials_enabled(self, enabled: bool) -> None:
        self.user_input.setEnabled(enabled)
        self.domain_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
