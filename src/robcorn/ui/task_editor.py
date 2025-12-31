from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class TaskEditor(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self.run_as_checkbox.setChecked(False)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QGridLayout()

        form.addWidget(QLabel("Label:"), 0, 0)
        self.label_input = QLineEdit()
        form.addWidget(self.label_input, 0, 1, 1, 3)

        form.addWidget(QLabel("Description:"), 1, 0)
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(60)
        form.addWidget(self.description_input, 1, 1, 1, 3)

        form.addWidget(QLabel("Send to:"), 2, 0)
        self.send_to_input = QLineEdit()
        form.addWidget(self.send_to_input, 2, 1, 1, 2)
        self.send_to_browse = QPushButton("...")
        form.addWidget(self.send_to_browse, 2, 3)

        program_group = QGroupBox("Program")
        program_layout = QGridLayout(program_group)
        program_layout.addWidget(QLabel("Program:"), 0, 0)
        self.program_input = QLineEdit()
        program_layout.addWidget(self.program_input, 0, 1)
        self.program_browse = QPushButton("...")
        program_layout.addWidget(self.program_browse, 0, 2)
        self.tools_button = QPushButton("Tools")
        program_layout.addWidget(self.tools_button, 0, 3)

        program_layout.addWidget(QLabel("Parameter:"), 1, 0)
        self.parameters_input = QLineEdit()
        program_layout.addWidget(self.parameters_input, 1, 1)
        self.parameters_browse = QPushButton("...")
        program_layout.addWidget(self.parameters_browse, 1, 2)

        program_layout.addWidget(QLabel("Batchfile:"), 2, 0)
        self.batch_input = QLineEdit()
        program_layout.addWidget(self.batch_input, 2, 1)
        self.batch_browse = QPushButton("...")
        program_layout.addWidget(self.batch_browse, 2, 2)
        self.batch_button = QPushButton("Batch")
        program_layout.addWidget(self.batch_button, 2, 3)

        self.api_checkbox = QCheckBox("Send API request")
        self.api_button = QPushButton("Configure")
        program_layout.addWidget(self.api_checkbox, 3, 0, 1, 2)
        program_layout.addWidget(self.api_button, 3, 2, 1, 2)

        form.addWidget(program_group, 3, 0, 1, 4)

        toggles = QVBoxLayout()
        self.active_checkbox = QCheckBox("Activate task")
        self.once_checkbox = QCheckBox("Once per day")
        self.autostart_checkbox = QCheckBox("Autostart")
        self.run_as_checkbox = QCheckBox("RunAs Job")
        for checkbox in (self.active_checkbox, self.once_checkbox, self.autostart_checkbox, self.run_as_checkbox):
            toggles.addWidget(checkbox)

        form.addLayout(toggles, 0, 4, 3, 1)
        root.addLayout(form)

        button_row = QHBoxLayout()
        button_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.new_button = QPushButton("Create new CronJob")
        self.start_button = QPushButton("Start")
        self.delete_button = QPushButton("Delete")
        self.help_button = QPushButton("Help")
        self.save_button = QPushButton("Save")
        self.exit_button = QPushButton("Exit")
        for button in (
            self.new_button,
            self.start_button,
            self.delete_button,
            self.help_button,
            self.save_button,
            self.exit_button,
        ):
            button_row.addWidget(button)

        root.addLayout(button_row)

        self.program_browse.clicked.connect(self._browse_program)
        self.batch_browse.clicked.connect(self._browse_batch)
        self.parameters_browse.clicked.connect(self._browse_parameters)
        self.send_to_browse.clicked.connect(self._browse_send_to)
        self.batch_button.clicked.connect(self._browse_batch)
        self.api_button.setEnabled(False)
        self.api_checkbox.toggled.connect(self.api_button.setEnabled)

    def _browse_program(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Program")
        if path:
            self.program_input.setText(path)

    def _browse_batch(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Batch File", filter="Batch Files (*.bat *.cmd)")
        if path:
            self.batch_input.setText(path)

    def _browse_parameters(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if path:
            if " " in path:
                self.parameters_input.setText(f"\"{path}\"")
            else:
                self.parameters_input.setText(path)

    def _browse_send_to(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Target")
        if path:
            self.send_to_input.setText(path)
