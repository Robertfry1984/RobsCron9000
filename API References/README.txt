RobCron Scheduler API Reference

Base URL:
  http://127.0.0.1:11349

Endpoints:
  GET    /tasks
  POST   /tasks
  PUT    /tasks/{id}
  DELETE /tasks/{id}

Examples:
  get_all_tasks.json
  create_task.json
  update_or_delete_task.json

Fields:
  name, description, send_to, program_path, parameters, batch_path
  active, once_per_day, autostart
  run_as_enabled, run_as_admin, run_as_user, run_as_domain, run_as_password
  api_enabled, api_method, api_url, api_headers, api_body, api_auth_type,
  api_auth_value, api_timeout, api_retries

Schedules:
  schedule_type: "recurring" | "date" | "monthly"
  days_mask: bitmask for weekdays (Mon=1, Tue=2, ... Sun=64)
  date: "YYYY-MM-DD" for date schedules, "DD" for monthly
  minute_of_day: 0..1439 (e.g., 300 = 05:00)
  active: true/false
