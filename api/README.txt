RobCron API service

Start:
  python api/server.py

This starts a local-only HTTP server on 127.0.0.1:11349 by default.
Set ROBCORN_API_PORT in .env to change the port per clone.
On startup it attempts to free the port if another process is listening.

Endpoints:
  GET /tasks
  POST /tasks
  PUT /tasks/{id}
  DELETE /tasks/{id}

POST/PUT body shape (JSON):
{
  "name": "Example",
  "description": "",
  "send_to": "",
  "program_path": "C:\\Windows\\System32\\notepad.exe",
  "parameters": "\"C:\\Path To\\file.txt\"",
  "batch_path": "",
  "active": true,
  "once_per_day": false,
  "autostart": false,
  "run_as_enabled": false,
  "run_as_admin": false,
  "run_as_user": "",
  "run_as_domain": "",
  "run_as_password": "",
  "schedules": [
    {
      "schedule_type": "recurring",
      "days_mask": 127,
      "date": null,
      "minute_of_day": 300,
      "active": true
    }
  ]
}
