from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QStatusBar,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..config import db_path
from ..repository import Repository
from ..runner import JobRunner
from ..scheduler import SchedulerEngine
from .log_view import LogView
from .scheduler_dialog import SchedulerDialog
from .settings_view import SettingsView
from .task_editor_dialog import TaskEditorDialog
from ..windows import create_shortcut
from .utils import summarize_job


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RobCron")
        icon_path = Path(__file__).resolve().parents[2] / "Images" / "robcorn.svg"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(980, 620)
        self._repository = Repository(db_path())
        self._repository.init()
        self._scheduler = SchedulerEngine(db_path())
        self._scheduler.start()
        self._runner = JobRunner(db_path())
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._jobs = []
        self._copied_job = None
        self._build_ui()
        self._start_clock()
        self._load_jobs()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(10, 10, 10, 10)

        top_nav_widget = QWidget()
        top_nav = QHBoxLayout(top_nav_widget)
        top_nav.setContentsMargins(10, 0, 0, 0)
        top_nav.setSpacing(6)
        self.task_tab = QPushButton("Task")
        self.log_tab = QPushButton("Log file")
        self.today_tab = QPushButton("Today")
        self.program_tab = QPushButton("Program")
        for button in (self.task_tab, self.log_tab, self.today_tab, self.program_tab):
            button_font = button.font()
            button_font.setPointSize(button_font.pointSize() + 2)
            button.setFont(button_font)
            button.setMinimumHeight(28)
            top_nav.addWidget(button, 1)
        layout.addWidget(top_nav_widget)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        tasks_panel = QWidget()
        tasks_layout = QVBoxLayout(tasks_panel)
        tasks_layout.setContentsMargins(10, 0, 0, 0)

        header = QLabel("Planned Tasks:")
        header.setAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setObjectName("sectionHeader")
        tasks_layout.addWidget(header)

        self.task_table = QTableWidget(0, 3)
        self.task_table.setHorizontalHeaderLabels(["Task", "Status", "Next Run"])
        self.task_table.horizontalHeader().setStretchLastSection(True)
        table_font = self.task_table.font()
        table_font.setPointSize(table_font.pointSize() + 2)
        self.task_table.setFont(table_font)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.verticalHeader().setDefaultSectionSize(28)
        self.task_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self._show_task_menu)
        tasks_layout.addWidget(self.task_table)

        actions = QToolBar()
        actions.setMovable(False)
        self.new_button = QPushButton("Create new CronJob")
        self.start_button = QPushButton("Start")
        self.delete_button = QPushButton("Delete")
        self.refresh_button = QPushButton("Refresh")
        self.save_button = QPushButton("Save")
        for button in (
            self.new_button,
            self.start_button,
            self.delete_button,
            self.refresh_button,
            self.save_button,
        ):
            button_font = button.font()
            button_font.setPointSize(button_font.pointSize() + 2)
            button.setFont(button_font)
            actions.addWidget(button)
        actions_container = QHBoxLayout()
        actions_container.addStretch(1)
        actions_container.addWidget(actions)
        actions_container.addStretch(1)
        tasks_layout.addLayout(actions_container)
        actions.setIconSize(QSize(20, 20))
        self._set_toolbar_icons()

        self.stack.addWidget(tasks_panel)
        self.log_view = LogView(self._repository)
        self.stack.addWidget(self.log_view)
        self.settings_view = SettingsView(self._repository)
        self.stack.addWidget(self.settings_view)
        self.setCentralWidget(root)

        self._apply_theme()
        self._set_active_tab(self.task_tab)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self._time_label = QLabel("")
        self._health_label = QLabel("Scheduler: ok")
        self._task_label = QLabel("Task N: -")
        self._program_label = QLabel("Program: -")
        self._refresh_label = QLabel("Last refresh: -")
        self._status_center = QLabel("")
        self._status_center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status.addWidget(self._status_center, 1)
        self.setStatusBar(status)

        self.new_button.clicked.connect(self._open_new_task)
        self.start_button.clicked.connect(self._start_selected_job)
        self.delete_button.clicked.connect(self._delete_selected_job)
        self.save_button.clicked.connect(self._edit_selected_job)
        self.refresh_button.clicked.connect(self._load_jobs)
        self.task_tab.clicked.connect(lambda: self._switch_view(0))
        self.log_tab.clicked.connect(lambda: self._switch_view(1))
        self.today_tab.clicked.connect(lambda: self._switch_view(2))
        self.program_tab.clicked.connect(lambda: self._switch_view(3))
        self.task_table.cellDoubleClicked.connect(self._edit_selected_job)
        self.task_table.itemSelectionChanged.connect(self._update_status_bar)

    def _show_task_menu(self, pos) -> None:
        menu = QMenu(self)
        scheduler_action = menu.addAction("Scheduler")
        start_action = menu.addAction("Start")
        delete_action = menu.addAction("Delete")
        copy_action = menu.addAction("Copy")
        paste_action = menu.addAction("Paste")
        cleanup_action = menu.addAction("Clean up")
        shortcut_action = menu.addAction("Shortcut")
        scheduler_action.triggered.connect(self._open_scheduler)
        start_action.triggered.connect(self._start_selected_job)
        delete_action.triggered.connect(self._delete_selected_job)
        copy_action.triggered.connect(self._copy_job)
        paste_action.triggered.connect(self._paste_job)
        cleanup_action.triggered.connect(self._cleanup_logs)
        shortcut_action.triggered.connect(self._create_shortcut)
        menu.exec(self.task_table.mapToGlobal(pos))

    def _start_clock(self) -> None:
        timer = QTimer(self)
        timer.timeout.connect(self._update_time)
        timer.start(1000)
        self._update_time()
        self._clock_timer = timer

        scheduler_timer = QTimer(self)
        scheduler_timer.timeout.connect(self._scheduler.ensure_running)
        scheduler_timer.start(10_000)
        self._scheduler_timer = scheduler_timer

        log_timer = QTimer(self)
        log_timer.timeout.connect(self.log_view.refresh)
        log_timer.start(30_000)
        self._log_timer = log_timer

        health_timer = QTimer(self)
        health_timer.timeout.connect(self._update_health)
        health_timer.start(5_000)
        self._health_timer = health_timer

    def _update_time(self) -> None:
        self._time_label.setText(datetime.now().strftime("%H:%M:%S"))
        self._update_status_text()

    def _update_health(self) -> None:
        running = self._scheduler.is_running()
        self._health_label.setText("Scheduler: ok" if running else "Scheduler: stopped")
        self._update_status_text()

    def _update_status_bar(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            self._task_label.setText("Task N: -")
            self._program_label.setText("Program: -")
            self._update_status_text()
            return
        job = self._jobs[row]
        self._task_label.setText(f"Task N: {job.id}")
        self._program_label.setText(f"Program: {summarize_job(job)}")
        self._update_status_text()

    def _update_status_text(self) -> None:
        self._status_center.setText(
            f"{self._task_label.text()} | {self._program_label.text()} | "
            f"{self._refresh_label.text()} | {self._time_label.text()} | {self._health_label.text()}"
        )

    def _open_new_task(self) -> None:
        dialog = TaskEditorDialog(self._repository, parent=self)
        if dialog.exec():
            self._load_jobs()

    def _load_jobs(self) -> None:
        self._jobs = self._repository.list_jobs()
        self.task_table.setRowCount(len(self._jobs))
        for row_index, job in enumerate(self._jobs):
            task_label = f"{job.name} ({summarize_job(job)})"
            self.task_table.setItem(row_index, 0, QTableWidgetItem(task_label))
            status_text = "● Active" if job.active else "● Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setForeground(Qt.GlobalColor.green if job.active else Qt.GlobalColor.lightGray)
            self.task_table.setItem(row_index, 1, status_item)
            next_run = self._repository.next_run_for_job(job.id)
            next_text = next_run.isoformat(timespec="minutes") if next_run else ""
            self.task_table.setItem(row_index, 2, QTableWidgetItem(next_text))
        self.log_view.refresh()
        self._refresh_label.setText(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        self._update_status_bar()

    def _open_scheduler(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        job = self._jobs[row]
        dialog = SchedulerDialog(self)
        dialog.activate_checkbox.setChecked(True)
        slots = self._repository.list_schedule_slots(job.id)
        if slots:
            dialog.set_selected_minutes([slot.minute_of_day for slot in slots])
            schedule_type = slots[0].schedule_type
            dialog.set_schedule_type(schedule_type)
            dialog.set_days_mask(slots[0].days_mask)
            dialog.set_schedule_date(slots[0].date or "")
            dialog.activate_checkbox.setChecked(slots[0].active)
        if dialog.exec():
            minutes = dialog.selected_minutes()
            schedule_type = dialog.schedule_type()
            days_mask = dialog.days_mask() if schedule_type == "recurring" else 0
            date_value = dialog.schedule_date() if schedule_type in ("date", "monthly") else None
            self._repository.replace_schedule_slots(
                job_id=job.id,
                schedule_type=schedule_type,
                slots=minutes,
                days_mask=days_mask,
                date=date_value,
            )
            self._repository.set_schedule_active(job.id, dialog.activate_checkbox.isChecked())

    def _switch_view(self, index: int) -> None:
        if index == 1:
            self.stack.setCurrentWidget(self.log_view)
            self._set_active_tab(self.log_tab)
        elif index == 3:
            self.stack.setCurrentWidget(self.settings_view)
            self._set_active_tab(self.program_tab)
        else:
            self.stack.setCurrentIndex(0)
            self._set_active_tab(self.task_tab if index == 0 else self.today_tab)

    def closeEvent(self, event) -> None:
        self._scheduler.stop()
        self._executor.shutdown(wait=False)
        super().closeEvent(event)

    def _edit_selected_job(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        job = self._jobs[row]
        dialog = TaskEditorDialog(self._repository, job=job, parent=self)
        if dialog.exec():
            self._load_jobs()

    def _delete_selected_job(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        job = self._jobs[row]
        confirm = QMessageBox.question(
            self,
            "Delete",
            f"Delete job '{job.name}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._repository.delete_job(job.id)
        self._load_jobs()

    def _start_selected_job(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        job = self._jobs[row]
        scheduled_time = datetime.now().replace(second=0, microsecond=0)
        self._executor.submit(self._run_now, job, scheduled_time)

    def _run_now(self, job, scheduled_time) -> None:
        result = self._runner.run_job(job, scheduled_time)
        self._runner.persist_run(job.id, scheduled_time, result)

    def _copy_job(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        self._copied_job = self._jobs[row]

    def _paste_job(self) -> None:
        if not self._copied_job:
            return
        job = self._copied_job
        new_id = self._repository.create_job(
            name=f"{job.name} Copy",
            description=job.description,
            send_to=job.send_to,
            program_path=job.program_path,
            parameters=job.parameters,
            batch_path=job.batch_path,
            api_enabled=job.api_enabled,
            api_method=job.api_method,
            api_url=job.api_url,
            api_headers=job.api_headers,
            api_body=job.api_body,
            active=job.active,
            once_per_day=job.once_per_day,
            autostart=job.autostart,
            run_as_enabled=job.run_as_enabled,
            run_as_admin=job.run_as_admin,
            run_as_user=job.run_as_user,
            run_as_domain=job.run_as_domain,
            run_as_password=job.run_as_password,
        )
        slots = self._repository.list_schedule_slots(job.id)
        if slots:
            self._repository.replace_schedule_slots(
                job_id=new_id,
                schedule_type=slots[0].schedule_type,
                slots=[slot.minute_of_day for slot in slots],
                days_mask=slots[0].days_mask,
                date=slots[0].date,
            )
            self._repository.set_schedule_active(new_id, slots[0].active)
        self._load_jobs()

    def _cleanup_logs(self) -> None:
        self._repository.cleanup_logs()
        self.log_view.refresh()

    def _create_shortcut(self) -> None:
        row = self.task_table.currentRow()
        if row < 0 or row >= len(self._jobs):
            return
        job = self._jobs[row]
        if not job.program_path or job.program_path.startswith("tool:"):
            return
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / f"{job.name}.lnk"
        create_shortcut(shortcut_path, Path(job.program_path))

    def _set_toolbar_icons(self) -> None:
        style = self.style()
        self.new_button.setIcon(style.standardIcon(style.StandardPixmap.SP_FileDialogNewFolder))
        self.start_button.setIcon(style.standardIcon(style.StandardPixmap.SP_MediaPlay))
        self.delete_button.setIcon(style.standardIcon(style.StandardPixmap.SP_TrashIcon))
        self.refresh_button.setIcon(style.standardIcon(style.StandardPixmap.SP_BrowserReload))
        self.save_button.setIcon(style.standardIcon(style.StandardPixmap.SP_DialogSaveButton))

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #08111d, stop:0.4 #112b47, stop:0.7 #1b3f63, stop:1 #0a1b2d);
                color: #f0f4ff;
            }
            QLabel {
                background: transparent;
            }
            QGroupBox, QGroupBox::title {
                background: transparent;
            }
            QCheckBox {
                background: transparent;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #3a5c84;
                border-radius: 3px;
                background-color: #0b1624;
            }
            QCheckBox::indicator:checked {
                background-color: #2ecc71;
                border: 1px solid #2ecc71;
            }
            QTableWidget, QTableWidget::item {
                background-color: #0f2236;
                color: #f0f4ff;
            }
            QTableWidget::item:alternate {
                background-color: #102841;
            }
            QHeaderView::section {
                background-color: #17324d;
                color: #f0f4ff;
            }
            QTableWidget::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #3a5c84;
                border-radius: 3px;
                background-color: #0b1624;
            }
            QTableWidget::indicator:checked {
                background-color: #2ecc71;
                border: 1px solid #2ecc71;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #22476c, stop:1 #152c45);
                color: #f0f4ff;
                border: 1px solid #223a57;
                border-bottom: 2px solid #0f2236;
                padding: 4px 8px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                            stop:0 #2a557f, stop:1 #1a3552);
            }
            QToolBar {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QToolButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton[active="true"] {
                background-color: #2a4f7a;
                border: 1px solid #3a6ea5;
                font-weight: bold;
            }
            #sectionHeader {
                padding: 4px 0px 6px 2px;
                border-bottom: 1px solid #1c3451;
            }
            """
        )

    def _set_active_tab(self, button: QPushButton) -> None:
        for tab in (self.task_tab, self.log_tab, self.today_tab, self.program_tab):
            tab.setProperty("active", "false")
            tab.style().unpolish(tab)
            tab.style().polish(tab)
        button.setProperty("active", "true")
        button.style().unpolish(button)
        button.style().polish(button)


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
