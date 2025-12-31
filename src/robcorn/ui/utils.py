from __future__ import annotations

from ..models import Job


def summarize_job(job: Job) -> str:
    if job.program_path.startswith("tool:"):
        tool_name = job.program_path.split("tool:", 1)[-1]
        return f"Tool: {tool_name}"
    if job.program_path:
        return job.program_path
    if job.batch_path:
        return job.batch_path
    return "No target configured"
