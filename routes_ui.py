"""
routes_ui.py — Jinja2 page route handlers.

Serves the HTML templates via FastAPI + Jinja2Templates.
All routes are GET-only; actual pipeline work is done through api_routes.py.
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

import job_store

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=template_path)
print("TEMPLATE DIR:", template_path)

router = APIRouter(tags=["ui"])


# ── Home / Onboarding ─────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def onboarding(request: Request):
    return templates.TemplateResponse(request=request, name="onboarding.html")


# ── Input panel ───────────────────────────────────────────────────────────────

@router.get("/input", response_class=HTMLResponse)
async def input_page(request: Request):
    suggestions = [
        "Largest Element in an Array",
        "Linear Search",
        "Move Zeros to End",
        "Left Rotate an Array by One Place",
        "Find Missing Number in an Array",
        "Maximum Consecutive Ones",
    ]
    return templates.TemplateResponse(
        request=request, name="input.html", context={"suggestions": suggestions}
    )


# ── Pipeline visualization (live step tracker) ────────────────────────────────

@router.get("/pipeline/{job_id}", response_class=HTMLResponse)
async def pipeline_view(request: Request, job_id: str):
    job = job_store.get_job(job_id)
    return templates.TemplateResponse(
        request=request, name="pipeline.html",
        context={
            "job_id":  job_id,
            "problem": job["problem"] if job else "",
        },
    )


# ── Output view (Blockly + Python + IR + Logs) ────────────────────────────────

@router.get("/output/{job_id}", response_class=HTMLResponse)
async def output_view(request: Request, job_id: str):
    job = job_store.get_job(job_id)
    if not job:
        return templates.TemplateResponse(
            request=request, name="onboarding.html",
            context={"error": f"Job '{job_id}' not found."},
        )

    return templates.TemplateResponse(
        request=request, name="output.html",
        context={
            "job_id":             job_id,
            "problem":            job.get("problem", ""),
            "status":             job.get("status"),
            "fallback_triggered": job.get("fallback_triggered", False),
            "fallback_reason":    job.get("fallback_reason"),
            "elapsed_ms":         job.get("elapsed_ms"),
        },
    )


# ── Batch dashboard ───────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    jobs = job_store.all_jobs()
    recent = list(reversed(jobs))[:20]
    return templates.TemplateResponse(
        request=request, name="dashboard.html", context={"recent_jobs": recent}
    )
