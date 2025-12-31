from __future__ import annotations

import csv
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..repository import Repository


class LogView(QWidget):
    def __init__(self, repository: Repository):
        super().__init__()
        self._repository = repository
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self._export_csv)
        layout.addWidget(self.export_button)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Job", "Scheduled", "Status", "Exit Code"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._show_details)
        layout.addWidget(self.table)
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setFixedHeight(120)
        layout.addWidget(self.details)

    def refresh(self) -> None:
        logs = self._repository.list_run_logs()
        self.table.setRowCount(len(logs))
        for row_index, log in enumerate(logs):
            job_label = f"{log.job_name} (#{log.job_id})" if log.job_name else f"#{log.job_id}"
            job_item = QTableWidgetItem(job_label)
            job_item.setData(Qt.ItemDataRole.UserRole, log.job_id)
            self.table.setItem(row_index, 0, job_item)
            self.table.setItem(row_index, 1, QTableWidgetItem(log.scheduled_time.isoformat(timespec="minutes")))
            self.table.setItem(row_index, 2, QTableWidgetItem(log.status))
            exit_code = "" if log.exit_code is None else str(log.exit_code)
            self.table.setItem(row_index, 3, QTableWidgetItem(exit_code))
        if logs:
            self.table.selectRow(0)
        else:
            self.details.clear()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Logs", "robcorn_logs.csv", "CSV Files (*.csv)")
        if not path:
            return
        logs = self._repository.list_run_logs(limit=5000)
        output_path = Path(path)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["job_id", "job_name", "scheduled_time", "status", "exit_code"])
            for log in logs:
                writer.writerow(
                    [
                        log.job_id,
                        log.job_name,
                        log.scheduled_time.isoformat(timespec="minutes"),
                        log.status,
                        "" if log.exit_code is None else log.exit_code,
                    ]
                )

    def _show_details(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            self.details.clear()
            return
        scheduled_item = self.table.item(row, 1)
        if not scheduled_item:
            self.details.clear()
            return
        job_id = int(self.table.item(row, 0).data(Qt.ItemDataRole.UserRole))
        scheduled_time = scheduled_item.text()
        details = self._repository.get_run_log_details(job_id, scheduled_time)
        self.details.setPlainText(details)
