from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
)

from ..repository import Repository
from ..runner import JobRunner
from ..validation import validate_api_auth, validate_api_request, validate_job_targets, validate_run_as, validate_send_to
from .run_as_settings import RunAsSettings
from .scheduler_dialog import SchedulerPanel
from .task_editor import TaskEditor
from .api_request_dialog import ApiRequestDialog
from .tools_dialog import ToolsDialog


class TaskEditorDialog(QDialog):
    def __init__(self, repository: Repository, job=None, parent=None):
        super().__init__(parent)
        self._repository = repository
        self._job = job
        self._runner = JobRunner(repository.db_path)
        self._job_ids = [item.id for item in self._repository.list_jobs()]
        self._loading_job = False
        self.setWindowTitle("Z-Cron Task")
        self.resize(980, 560)
        self._editor = TaskEditor()
        self._scheduler = SchedulerPanel()
        self._run_as = RunAsSettings()
        self._api_method = ""
        self._api_url = ""
        self._api_headers = ""
        self._api_body = ""
        self._api_auth_type = ""
        self._api_auth_value = ""
        self._api_timeout = 0
        self._api_retries = 0
        self._build_ui()
        self._scheduler.activate_checkbox.setChecked(True)
        if self._job:
            self._load_job()
        else:
            self.setWindowTitle("Settings Job N: New")
            self.job_spin.setValue(max(self._job_ids, default=1))

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("Job N:"))
        self.prev_button = QToolButton()
        self.prev_button.setText("<")
        self.next_button = QToolButton()
        self.next_button.setText(">")
        self.job_spin = QSpinBox()
        self.job_spin.setMinimum(1)
        self.job_spin.setMaximum(max(self._job_ids, default=1))
        self.job_spin.setFixedWidth(72)
        self.job_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.prev_button.setFixedWidth(24)
        self.next_button.setFixedWidth(24)
        header.addWidget(self.prev_button)
        header.addWidget(self.job_spin)
        header.addWidget(self.next_button)
        header.addStretch(1)
        layout.addLayout(header)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._editor, "Rob-Cron Task")
        self._tabs.addTab(self._scheduler, "Scheduler")
        self._tabs.addTab(self._run_as, "Run As Settings")
        layout.addWidget(self._tabs)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self._editor.save_button.clicked.connect(self._save)
        self._editor.exit_button.clicked.connect(self.reject)
        self._editor.tools_button.clicked.connect(self._open_tools)
        self._editor.start_button.clicked.connect(self._start_job_now)
        self._editor.run_as_checkbox.toggled.connect(self._run_as.set_credentials_enabled)
        self._run_as.set_credentials_enabled(False)
        self._editor.delete_button.clicked.connect(self._delete_job)
        self._editor.new_button.clicked.connect(self._new_job)
        self._editor.help_button.clicked.connect(self._help_task)
        self._editor.api_button.clicked.connect(self._configure_api)
        self._editor.setStyleSheet("QLineEdit, QTextEdit { background: #ffffff; color: #000000; }")
        self.prev_button.clicked.connect(self._prev_job)
        self.next_button.clicked.connect(self._next_job)
        self.job_spin.valueChanged.connect(self._job_spin_changed)

    def _save(self) -> None:
        errors = []
        errors.extend(
            validate_job_targets(
                self._editor.program_input.text().strip(),
                self._editor.batch_input.text().strip(),
            )
        )
        errors.extend(validate_send_to(self._editor.send_to_input.text().strip()))
        errors.extend(
            validate_run_as(
                self._editor.run_as_checkbox.isChecked(),
                self._run_as.admin_checkbox.isChecked(),
                self._run_as.user_input.text().strip(),
                self._run_as.password_input.text(),
            )
        )
        errors.extend(
            validate_api_request(
                self._editor.api_checkbox.isChecked(),
                self._api_method,
                self._api_url,
            )
        )
        errors.extend(
            validate_api_auth(
                self._editor.api_checkbox.isChecked(),
                self._api_auth_type,
                self._api_auth_value,
            )
        )
        if errors:
            QMessageBox.warning(self, "Validation", "\n".join(errors))
            return

        if self._job:
            self._repository.update_job(
                job_id=self._job.id,
                name=self._editor.label_input.text().strip() or "New Job",
                description=self._editor.description_input.toPlainText().strip(),
                send_to=self._editor.send_to_input.text().strip(),
                program_path=self._editor.program_input.text().strip(),
                parameters=self._editor.parameters_input.text().strip(),
                batch_path=self._editor.batch_input.text().strip(),
                api_enabled=self._editor.api_checkbox.isChecked(),
                api_method=self._api_method,
                api_url=self._api_url,
                api_headers=self._api_headers,
                api_body=self._api_body,
                api_auth_type=self._api_auth_type,
                api_auth_value=self._api_auth_value,
                api_timeout=self._api_timeout,
                api_retries=self._api_retries,
                active=self._editor.active_checkbox.isChecked(),
                once_per_day=self._editor.once_checkbox.isChecked(),
                autostart=self._editor.autostart_checkbox.isChecked(),
                run_as_enabled=self._editor.run_as_checkbox.isChecked(),
                run_as_admin=self._run_as.admin_checkbox.isChecked(),
                run_as_user=self._run_as.user_input.text().strip(),
                run_as_domain=self._run_as.domain_input.text().strip(),
                run_as_password=self._run_as.password_input.text(),
            )
            job_id = self._job.id
        else:
            job_id = self._repository.create_job(
                name=self._editor.label_input.text().strip() or "New Job",
                description=self._editor.description_input.toPlainText().strip(),
                send_to=self._editor.send_to_input.text().strip(),
                program_path=self._editor.program_input.text().strip(),
                parameters=self._editor.parameters_input.text().strip(),
                batch_path=self._editor.batch_input.text().strip(),
                api_enabled=self._editor.api_checkbox.isChecked(),
                api_method=self._api_method,
                api_url=self._api_url,
                api_headers=self._api_headers,
                api_body=self._api_body,
                api_auth_type=self._api_auth_type,
                api_auth_value=self._api_auth_value,
                api_timeout=self._api_timeout,
                api_retries=self._api_retries,
                active=self._editor.active_checkbox.isChecked(),
                once_per_day=self._editor.once_checkbox.isChecked(),
                autostart=self._editor.autostart_checkbox.isChecked(),
                run_as_enabled=self._editor.run_as_checkbox.isChecked(),
                run_as_admin=self._run_as.admin_checkbox.isChecked(),
                run_as_user=self._run_as.user_input.text().strip(),
                run_as_domain=self._run_as.domain_input.text().strip(),
                run_as_password=self._run_as.password_input.text(),
            )
            self._job = self._repository.get_job(job_id)
            self._refresh_job_ids()
            self.job_spin.setMaximum(max(self._job_ids, default=1))
            self.job_spin.setValue(job_id)

        minutes = self._scheduler.selected_minutes()
        schedule_type = self._scheduler.schedule_type()
        days_mask = self._scheduler.days_mask() if schedule_type == "recurring" else 0
        date_value = self._scheduler.schedule_date() if schedule_type in ("date", "monthly") else None
        if minutes:
            self._repository.replace_schedule_slots(
                job_id=job_id,
                schedule_type=schedule_type,
                slots=minutes,
                days_mask=days_mask,
                date=date_value,
            )
            self._repository.set_schedule_active(job_id, self._scheduler.activate_checkbox.isChecked())
        else:
            self._repository.replace_schedule_slots(
                job_id=job_id,
                schedule_type="recurring",
                slots=[],
                days_mask=0,
                date=None,
            )
        self.accept()

    def _load_job(self) -> None:
        job = self._job
        self.setWindowTitle(f"Settings Job N: {job.id}")
        self._loading_job = True
        self.job_spin.setValue(job.id)
        self._loading_job = False
        self._editor.label_input.setText(job.name)
        self._editor.description_input.setPlainText(job.description)
        self._editor.send_to_input.setText(job.send_to)
        self._editor.program_input.setText(job.program_path)
        self._editor.parameters_input.setText(job.parameters)
        self._editor.batch_input.setText(job.batch_path)
        self._editor.api_checkbox.setChecked(job.api_enabled)
        self._editor.api_button.setEnabled(job.api_enabled)
        self._api_method = job.api_method
        self._api_url = job.api_url
        self._api_headers = job.api_headers
        self._api_body = job.api_body
        self._api_auth_type = job.api_auth_type
        self._api_auth_value = job.api_auth_value
        self._api_timeout = job.api_timeout
        self._api_retries = job.api_retries
        self._editor.active_checkbox.setChecked(job.active)
        self._editor.once_checkbox.setChecked(job.once_per_day)
        self._editor.autostart_checkbox.setChecked(job.autostart)
        self._editor.run_as_checkbox.setChecked(job.run_as_enabled)
        self._run_as.set_credentials_enabled(job.run_as_enabled)
        self._run_as.admin_checkbox.setChecked(job.run_as_admin)
        self._run_as.user_input.setText(job.run_as_user)
        self._run_as.domain_input.setText(job.run_as_domain)
        self._run_as.password_input.setText(job.run_as_password)

        slots = self._repository.list_schedule_slots(job.id)
        if slots:
            self._scheduler.set_selected_minutes([slot.minute_of_day for slot in slots])
            self._scheduler.set_schedule_type(slots[0].schedule_type)
            self._scheduler.set_days_mask(slots[0].days_mask)
            self._scheduler.set_schedule_date(slots[0].date or "")
            self._scheduler.activate_checkbox.setChecked(slots[0].active)

    def _open_tools(self) -> None:
        dialog = ToolsDialog(self)
        if dialog.exec():
            tool, params = dialog.selected_tool()
            self._editor.program_input.setText(f"tool:{tool}")
            self._editor.parameters_input.setText(params)

    def _configure_api(self) -> None:
        def _log_result(result) -> None:
            if not self._job:
                return
            status = int(result.get("status", 0) or 0)
            self._repository.log_api_test(
                self._job.id,
                status,
                result.get("response", ""),
                result.get("error", ""),
            )

        dialog = ApiRequestDialog(
            method=self._api_method,
            url=self._api_url,
            headers=self._api_headers,
            body=self._api_body,
            auth_type=self._api_auth_type,
            auth_value=self._api_auth_value,
            timeout=self._api_timeout,
            retries=self._api_retries,
            log_callback=_log_result,
            parent=self,
        )
        if dialog.exec():
            (
                self._api_method,
                self._api_url,
                self._api_headers,
                self._api_body,
                self._api_auth_type,
                self._api_auth_value,
                self._api_timeout,
                self._api_retries,
            ) = dialog.get_values()

    def _start_job_now(self) -> None:
        if not self._job:
            QMessageBox.information(self, "Start", "Save the job before running it.")
            return
        scheduled_time = datetime.now().replace(second=0, microsecond=0)
        result = self._runner.run_job(self._job, scheduled_time)
        self._runner.persist_run(self._job.id, scheduled_time, result)
        if result.status == "success":
            QMessageBox.information(self, "Start", "Job completed.")
        else:
            QMessageBox.warning(self, "Start", result.error or "Job failed.")

    def _delete_job(self) -> None:
        if not self._job:
            return
        confirm = QMessageBox.question(
            self,
            "Delete",
            f"Delete job '{self._job.name}'?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._repository.delete_job(self._job.id)
        self.accept()

    def _new_job(self) -> None:
        dialog = TaskEditorDialog(self._repository, parent=self)
        dialog.exec()

    def _help_task(self) -> None:
        QMessageBox.information(
            self,
            "Task Help",
            "Fill in the program or batch file, then configure the Scheduler tab and Save.",
        )

    def _refresh_job_ids(self) -> None:
        self._job_ids = [item.id for item in self._repository.list_jobs()]

    def _job_spin_changed(self, value: int) -> None:
        if self._loading_job:
            return
        job = self._repository.get_job(value)
        if job:
            self._job = job
            self._load_job()

    def _prev_job(self) -> None:
        if not self._job_ids:
            return
        current = self.job_spin.value()
        smaller = [job_id for job_id in self._job_ids if job_id < current]
        if smaller:
            self.job_spin.setValue(max(smaller))

    def _next_job(self) -> None:
        if not self._job_ids:
            return
        current = self.job_spin.value()
        larger = [job_id for job_id in self._job_ids if job_id > current]
        if larger:
            self.job_spin.setValue(min(larger))
