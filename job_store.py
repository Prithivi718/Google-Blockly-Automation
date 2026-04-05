"""
job_store.py — In-memory job & batch state management.

Stores pipeline execution state for each job_id and batch_id.
All data lives in-process (no database required).
Can be swapped for Redis or SQLite later if needed.
"""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

# ──────────────────────────────────────────────
# In-memory stores
# ──────────────────────────────────────────────

_jobs: Dict[str, Dict[str, Any]] = {}
_batches: Dict[str, Dict[str, Any]] = {}


# ──────────────────────────────────────────────
# Step definitions (pipeline phases)
# ──────────────────────────────────────────────

PIPELINE_STEPS = [
    "Semantic Planning",
    "Validation",
    "IR Compilation",
    "XML Generation",
]


def _default_steps() -> List[Dict]:
    return [
        {"name": s, "status": "pending", "detail": None}
        for s in PIPELINE_STEPS
    ]


# ──────────────────────────────────────────────
# Job API
# ──────────────────────────────────────────────

def create_job(problem: str, pid: Optional[str] = None, batch_id: Optional[str] = None) -> str:
    """Create a new job entry and return its job_id."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = {
        "job_id":             job_id,
        "problem":            problem,
        "pid":                pid,
        "batch_id":           batch_id,
        "status":             "queued",          # queued | in_progress | completed | failed
        "current_step":       None,
        "steps":              _default_steps(),
        "xml":                None,
        "ir":                 None,
        "python":              None,
        "logs":               [],
        "fallback_triggered": False,
        "fallback_reason":    None,
        "error":              None,
        "problem_expansion":  None,
        "skeleton":           None,
        "created_at":         datetime.utcnow().isoformat(),
        "completed_at":       None,
        "elapsed_ms":         None,
    }
    return job_id


def get_job(job_id: str) -> Optional[Dict]:
    return _jobs.get(job_id)


def all_jobs() -> List[Dict]:
    return list(_jobs.values())


def update_step(job_id: str, step_name: str, status: str, detail: Optional[str] = None):
    """Mark a pipeline step as in_progress / completed / failed."""
    job = _jobs.get(job_id)
    if not job:
        return
    job["current_step"] = step_name
    for step in job["steps"]:
        if step["name"] == step_name:
            step["status"] = status
            if detail:
                step["detail"] = detail
            break
    if detail:
        job["logs"].append(f"[{step_name}] {detail}")


def set_job_result(
    job_id: str,
    xml: str,
    ir: Dict,
    logs: List[str],
    python: Optional[str] = None,
    expansion: Optional[str] = None,
    skeleton: Optional[str] = None,
    fallback: bool = False,
    fallback_reason: Optional[str] = None,
):
    job = _jobs.get(job_id)
    if not job:
        return
    job["status"]             = "completed"
    job["current_step"]       = None
    job["xml"]                = xml
    job["ir"]                 = ir
    job["python"]             = python
    job["problem_expansion"]  = expansion
    job["skeleton"]           = skeleton
    job["logs"].extend(logs)
    job["fallback_triggered"] = fallback
    job["fallback_reason"]    = fallback_reason
    job["completed_at"]       = datetime.utcnow().isoformat()
    # mark all remaining pending steps as completed
    for step in job["steps"]:
        if step["status"] == "pending":
            step["status"] = "completed"


def set_job_failed(job_id: str, error: str):
    job = _jobs.get(job_id)
    if not job:
        return
    job["status"]  = "failed"
    job["error"]   = error
    job["logs"].append(f"[ERROR] {error}")
    job["completed_at"] = datetime.utcnow().isoformat()
    for step in job["steps"]:
        if step["status"] == "in_progress":
            step["status"] = "failed"
            step["detail"] = error


def set_job_in_progress(job_id: str):
    job = _jobs.get(job_id)
    if job:
        job["status"] = "in_progress"


# ──────────────────────────────────────────────
# Batch API
# ──────────────────────────────────────────────

def create_batch(total: int) -> str:
    batch_id = "batch_" + str(uuid.uuid4())[:8]
    _batches[batch_id] = {
        "batch_id":  batch_id,
        "total":     total,
        "job_ids":   [],
        "status":    "queued",
        "created_at": datetime.utcnow().isoformat(),
    }
    return batch_id


def add_job_to_batch(batch_id: str, job_id: str):
    b = _batches.get(batch_id)
    if b:
        b["job_ids"].append(job_id)


def get_batch_status(batch_id: str) -> Optional[Dict]:
    b = _batches.get(batch_id)
    if not b:
        return None

    results = []
    completed = failed = 0

    for jid in b["job_ids"]:
        job = _jobs.get(jid, {})
        status = job.get("status", "unknown")
        entry = {
            "pid":      job.get("pid", jid),
            "job_id":   jid,
            "status":   "fallback" if job.get("fallback_triggered") else status,
            "problem":  job.get("problem"),
            "error":    job.get("error"),
            "elapsed_ms": job.get("elapsed_ms"),
        }
        results.append(entry)
        if status == "completed":
            completed += 1
        elif status == "failed":
            failed += 1

    in_progress = b["total"] - completed - failed
    overall = (
        "completed" if completed + failed == b["total"]
        else "in_progress" if completed + failed > 0
        else "queued"
    )

    return {
        "batch_id":    batch_id,
        "total":       b["total"],
        "completed":   completed,
        "failed":      failed,
        "in_progress": in_progress,
        "status":      overall,
        "results":     results,
        "created_at":  b["created_at"],
    }
