"""
app_ui.py — FastAPI application entrypoint for Google Blockly Agent UI.

Run with:
    uvicorn app_ui:app --reload --host 0.0.0.0 --port 8000

New files created:
    app_ui.py, routes_ui.py, api_routes.py, job_store.py, pipeline_runner.py
    templates/, static/

Existing files: UNCHANGED.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from api_routes import router as api_router
from routes_ui import router as ui_router

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="Google Blockly Agent UI",
    description="Interactive UI for the Google Blockly Agent pipeline.",
    version="1.0.0",
)

# Allow browser JS to call the API (useful when developing frontend separately)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Static files (CSS, JS, icons)
# ──────────────────────────────────────────────

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount official project libraries for Blockly
LIBS_DIR = Path(__file__).parent / "local_blockly" / "libs"
app.mount("/libs", StaticFiles(directory=str(LIBS_DIR)), name="libs")

# ──────────────────────────────────────────────
# Routers
# ──────────────────────────────────────────────

app.include_router(api_router)   # /api/* endpoints
app.include_router(ui_router)    # / /input /pipeline /output /dashboard


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Google Blockly Agent UI"}


# ──────────────────────────────────────────────
# Dev runner
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Google Blockly Agent UI is starting!")
    print("👉 Access the UI at: http://localhost:5000\n")
    uvicorn.run("app_ui:app", host="127.0.0.1", port=5000, reload=True)