from __future__ import annotations

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SchedulerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()
        self.activate_checkbox = QCheckBox("Activate task")
        left_panel.addWidget(self.activate_checkbox)
        period_group = QGroupBox("Period")
        period_layout = QVBoxLayout(period_group)
        self.month_checkbox = QCheckBox("Month")
        self.weekday_checkbox = QCheckBox("Weekday")
        self.date_checkbox = QCheckBox("Specific date")
        self.weekday_checkbox.setChecked(True)
        period_layout.addWidget(self.month_checkbox)
        period_layout.addWidget(self.weekday_checkbox)
        period_layout.addWidget(self.date_checkbox)
        left_panel.addWidget(period_group)
        self.day_checks = []
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
            checkbox = QCheckBox(day)
            checkbox.setChecked(True)
            self.day_checks.append(checkbox)
            left_panel.addWidget(checkbox)
        self.weekday_button = QPushButton("Weekday")
        self.weekend_button = QPushButton("Weekend")
        self.everyday_button = QPushButton("Every day")
        left_panel.addWidget(self.weekday_button)
        left_panel.addWidget(self.weekend_button)
        left_panel.addWidget(self.everyday_button)
        left_panel.addStretch(1)
        layout.addLayout(left_panel)

        right_panel = QVBoxLayout()
        header = QHBoxLayout()
        header.addWidget(QLabel("Scheduler"))
        header.addStretch(1)
        right_panel.addLayout(header)

        self.grid = QTableWidget(12, 24)
        self.grid.setHorizontalHeaderLabels([f"{i:02d}" for i in range(24)])
        self.grid.setVerticalHeaderLabels([f"{i*5:02d}" for i in range(12)])
        self.grid.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.grid.horizontalHeader().setDefaultSectionSize(28)
        self.grid.horizontalHeader().setMinimumSectionSize(24)
        self.grid.verticalHeader().setDefaultSectionSize(26)
        for row in range(12):
            for col in range(24):
                item = QTableWidgetItem("")
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self.grid.setItem(row, col, item)
        right_panel.addWidget(self.grid)

        footer = QGridLayout()
        self.help_button = QPushButton("?")
        footer.addWidget(self.help_button, 0, 0)
        self.delete_button = QPushButton("Delete")
        footer.addWidget(self.delete_button, 0, 1)
        self.date_label = QLabel("Date:")
        footer.addWidget(self.date_label, 0, 2)
        self.date_picker = QDateEdit()
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        footer.addWidget(self.date_picker, 0, 3)
        self.every_combo = QComboBox()
        self.every_combo.addItems(
            ["Every 5 minutes", "Every 10 minutes", "Every 15 minutes", "Every 30 minutes", "Every 60 minutes"]
        )
        footer.addWidget(self.every_combo, 0, 4)
        self.save_button = QPushButton("Save")
        footer.addWidget(self.save_button, 0, 5)
        right_panel.addLayout(footer)

        layout.addLayout(right_panel, 1)

        self.every_combo.currentIndexChanged.connect(self._apply_every_combo)
        self.month_checkbox.toggled.connect(lambda: self._set_period("monthly"))
        self.weekday_checkbox.toggled.connect(lambda: self._set_period("weekday"))
        self.date_checkbox.toggled.connect(lambda: self._set_period("date"))
        self.weekday_button.clicked.connect(self._select_weekday)
        self.weekend_button.clicked.connect(self._select_weekend)
        self.everyday_button.clicked.connect(self._select_everyday)
        self._toggle_mode()

    def selected_minutes(self) -> list[int]:
        minutes = []
        for row in range(12):
            for col in range(24):
                item = self.grid.item(row, col)
                if item and item.checkState() == Qt.CheckState.Checked:
                    minutes.append(col * 60 + row * 5)
        return minutes

    def set_selected_minutes(self, minutes: list[int]) -> None:
        minute_set = set(minutes)
        for row in range(12):
            for col in range(24):
                minute = col * 60 + row * 5
                item = self.grid.item(row, col)
                if item:
                    item.setCheckState(
                        Qt.CheckState.Checked if minute in minute_set else Qt.CheckState.Unchecked
                    )

    def apply_every_minutes(self, step: int) -> None:
        for row in range(12):
            for col in range(24):
                minute = col * 60 + row * 5
                item = self.grid.item(row, col)
                if item:
                    item.setCheckState(
                        Qt.CheckState.Checked if minute % step == 0 else Qt.CheckState.Unchecked
                    )

    def _apply_every_combo(self) -> None:
        text = self.every_combo.currentText()
        if " " in text:
            parts = text.split(" ")
            try:
                step = int(parts[1])
            except ValueError:
                return
            self.apply_every_minutes(step)

    def schedule_type(self) -> str:
        if self.date_checkbox.isChecked():
            return "date"
        if self.month_checkbox.isChecked():
            return "monthly"
        return "recurring"

    def days_mask(self) -> int:
        mask = 0
        for index, checkbox in enumerate(self.day_checks):
            if checkbox.isChecked():
                mask |= 1 << index
        return mask

    def schedule_date(self) -> str:
        if self.month_checkbox.isChecked():
            return f"{self.date_picker.date().day():02d}"
        return self.date_picker.date().toString("yyyy-MM-dd")

    def set_schedule_type(self, schedule_type: str) -> None:
        self.month_checkbox.setChecked(schedule_type == "monthly")
        self.date_checkbox.setChecked(schedule_type == "date")
        self.weekday_checkbox.setChecked(schedule_type == "recurring")

    def set_days_mask(self, mask: int) -> None:
        for index, checkbox in enumerate(self.day_checks):
            checkbox.setChecked(bool(mask & (1 << index)))

    def set_schedule_date(self, date_str: str) -> None:
        if date_str:
            if len(date_str) <= 2:
                day = int(date_str)
                current = QDate.currentDate()
                self.date_picker.setDate(QDate(current.year(), current.month(), day))
            else:
                date = QDate.fromString(date_str, "yyyy-MM-dd")
                if date.isValid():
                    self.date_picker.setDate(date)

    def _toggle_mode(self) -> None:
        is_recurring = self.weekday_checkbox.isChecked()
        for checkbox in self.day_checks:
            checkbox.setEnabled(is_recurring)
        show_date = self.month_checkbox.isChecked() or self.date_checkbox.isChecked()
        self.date_picker.setEnabled(show_date)
        self.date_label.setText("Day of month:" if self.month_checkbox.isChecked() else "Date:")

    def _set_period(self, mode: str) -> None:
        if mode == "monthly" and self.month_checkbox.isChecked():
            self.weekday_checkbox.setChecked(False)
            self.date_checkbox.setChecked(False)
        elif mode == "date" and self.date_checkbox.isChecked():
            self.month_checkbox.setChecked(False)
            self.weekday_checkbox.setChecked(False)
        elif mode == "weekday" and self.weekday_checkbox.isChecked():
            self.month_checkbox.setChecked(False)
            self.date_checkbox.setChecked(False)
        if not (self.month_checkbox.isChecked() or self.weekday_checkbox.isChecked() or self.date_checkbox.isChecked()):
            self.weekday_checkbox.setChecked(True)
        self._toggle_mode()

    def _select_weekday(self) -> None:
        self.weekday_checkbox.setChecked(True)
        for index, checkbox in enumerate(self.day_checks):
            checkbox.setChecked(index < 5)

    def _select_weekend(self) -> None:
        self.weekday_checkbox.setChecked(True)
        for index, checkbox in enumerate(self.day_checks):
            checkbox.setChecked(index >= 5)

    def _select_everyday(self) -> None:
        self.weekday_checkbox.setChecked(True)
        for checkbox in self.day_checks:
            checkbox.setChecked(True)


class SchedulerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scheduler")
        self.resize(780, 420)
        self._panel = SchedulerPanel(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self._panel)
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.ok_button = QPushButton("OK")
        button_row.addWidget(self.ok_button)
        layout.addLayout(button_row)
        self.ok_button.clicked.connect(self.accept)
        self._panel.save_button.clicked.connect(self.accept)

    def __getattr__(self, name: str):
        return getattr(self._panel, name)
