"""
api_routes.py — REST API handlers for the Google Blockly Agent UI.

All endpoints prefix: /api
No existing files are modified.
"""

import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import job_store
import pipeline_runner

router = APIRouter(prefix="/api", tags=["pipeline"])

ROOT = Path(__file__).parent


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    problem: str


class BatchProblem(BaseModel):
    problem_id: str
    description: str


class BatchRequest(BaseModel):
    team_id: Optional[str] = "TEAM_UI"
    problems: List[BatchProblem]


# ──────────────────────────────────────────────
# Single execution
# ──────────────────────────────────────────────

@router.post("/execute")
async def execute_single(req: ExecuteRequest):
    """
    Start the pipeline for a single problem.
    Returns job_id immediately; pipeline runs in background.
    """
    if not req.problem.strip():
        raise HTTPException(status_code=400, detail="Problem statement cannot be empty.")

    job_id = job_store.create_job(problem=req.problem.strip())
    pipeline_runner.run_job_async(job_id, req.problem.strip())

    return {"job_id": job_id, "status": "queued", "problem": req.problem.strip()}


# ──────────────────────────────────────────────
# Status polling
# ──────────────────────────────────────────────

@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """
    Poll current pipeline step + logs.
    Called every ~1.5s by the frontend pipeline view.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    return {
        "job_id":             job["job_id"],
        "status":             job["status"],
        "current_step":       job["current_step"],
        "steps":              job["steps"],
        "logs":               job["logs"],
        "fallback_triggered": job["fallback_triggered"],
        "fallback_reason":    job["fallback_reason"],
        "error":              job["error"],
    }


# ──────────────────────────────────────────────
# Full result (after completion)
# ──────────────────────────────────────────────

@router.get("/result/{job_id}")
async def get_result(job_id: str):
    """
    Return final XML, IR JSON, and all logs.
    Only meaningful once status == 'completed'.
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    if job["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=202, detail="Pipeline still running.")

    return {
        "job_id":             job["job_id"],
        "status":             job["status"],
        "problem":            job["problem"],
        "xml":                job["xml"],
        "ir":                 job["ir"],
        "python":             job.get("python"),
        "expansion":          job.get("problem_expansion"),
        "skeleton":           job.get("skeleton"),
        "logs":               job["logs"],
        "fallback_triggered": job["fallback_triggered"],
        "fallback_reason":    job["fallback_reason"],
        "error":              job["error"],
        "elapsed_ms":         job["elapsed_ms"],
    }


# ──────────────────────────────────────────────
# History
# ──────────────────────────────────────────────

@router.get("/history")
async def get_history():
    """Return a summary of all jobs (for the history sidebar)."""
    jobs = job_store.all_jobs()
    return {
        "total": len(jobs),
        "jobs": [
            {
                "job_id":   j["job_id"],
                "problem":  j["problem"],
                "status":   j["status"],
                "fallback": j["fallback_triggered"],
                "elapsed_ms": j["elapsed_ms"],
                "created_at": j["created_at"],
            }
            for j in reversed(jobs)
        ],
    }


# ──────────────────────────────────────────────
# Batch execution
# ──────────────────────────────────────────────

@router.post("/batch")
async def execute_batch(req: BatchRequest):
    """
    Start batch processing for multiple problems.
    Returns batch_id; each problem gets its own job_id running in background.
    """
    if not req.problems:
        raise HTTPException(status_code=400, detail="No problems provided.")

    batch_id = job_store.create_batch(total=len(req.problems))

    for p in req.problems:
        job_id = job_store.create_job(
            problem=p.description.strip(),
            pid=p.problem_id,
            batch_id=batch_id,
        )
        job_store.add_job_to_batch(batch_id, job_id)
        pipeline_runner.run_job_async(job_id, p.description.strip())

    return {
        "batch_id": batch_id,
        "total":    len(req.problems),
        "status":   "queued",
    }


@router.post("/batch/upload")
async def upload_batch(file: UploadFile = File(...)):
    """
    Accept a JSON file upload matching the problems.json schema.
    Kicks off a batch run and returns batch_id.
    """
    try:
        content = await file.read()
        data = json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    problems_raw = data.get("problems", [])
    if not problems_raw:
        raise HTTPException(status_code=400, detail="JSON must contain a 'problems' array.")

    problems = [
        BatchProblem(problem_id=p["problem_id"], description=p["description"])
        for p in problems_raw
    ]

    req = BatchRequest(team_id=data.get("team_id", "TEAM_UI"), problems=problems)
    return await execute_batch(req)


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Return aggregated status for all problems in a batch."""
    status = job_store.get_batch_status(batch_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found.")
    return status


# ──────────────────────────────────────────────
# Suggestion chips (for the input panel)
# ──────────────────────────────────────────────

@router.get("/suggestions")
async def get_suggestions():
    """Return a list of sample problems for the suggestion chips."""
    return {
        "suggestions": [
            "Largest Element in an Array",
            "Linear Search",
            "Move Zeros to End",
            "Left Rotate an Array by One Place",
            "Find Missing Number in an Array",
            "Maximum Consecutive Ones",
            "Sum of All Elements in a List",
        ]
    }
