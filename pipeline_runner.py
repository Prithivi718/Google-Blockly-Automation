"""
pipeline_runner.py — Orchestrates the IR-based pipeline.

Pipeline steps:
  1. Semantic Planning  — LLM produces Semantic IR JSON
  2. IR Validation      — CapabilityValidator checks IR structure (done inside planner)
  3. IR → Blockly       — SemanticCompiler translates IR (done inside planner)
  4. Normalization      — BlocklyCompiler ensures block tree is well-formed
  5. XML Generation     — Node generate_xml.js converts block_tree.json → program.xml

The planner now returns a fully compiled + validated Blockly block tree.
Fallback LLM is triggered when the strict pipeline raises any exception.
"""

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

# ── Existing modules (no modification) ────────────────────────────────────────
from semantic.planner import generate_semantic_plan, generate_semantic_plan_from_expansion, SemanticPlannerError
from semantic.question_expander import expand_problem
from semantic.validator import CapabilityValidator
from semantic.compiler import SemanticCompiler, BlocklyCompiler
from fallback_llm.llm_xml_generator import generate_fallback_outputs

import job_store

# ── Paths (mirrors main.py) ────────────────────────────────────────────────────
ROOT              = Path(__file__).parent
NORMALIZED_BLOCKS = ROOT / "data" / "normalized_blocks.json"
BLOCK_TREE_OUT    = ROOT / "semantic" / "output" / "block_tree.json"
XML_OUT           = ROOT / "assembler" / "output" / "program.xml"
ASSEMBLER_DIR     = ROOT / "assembler"


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _run_node(cwd: Path) -> str:
    """Run generate_xml.js and return its stdout."""
    result = subprocess.run(
        ["node", "generate_xml.js"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"generate_xml.js failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _read_xml() -> str:
    if XML_OUT.exists():
        return XML_OUT.read_text(encoding="utf-8")
    return "<xml></xml>"


def _log(job_id: str, message: str):
    job = job_store.get_job(job_id)
    if job:
        job["logs"].append(message)


# ──────────────────────────────────────────────────────────────────────────────
# Core pipeline (strict path)
# ──────────────────────────────────────────────────────────────────────────────

def _run_strict_pipeline(job_id: str, expansion: str):
    """
    Runs the strict pipeline and updates job_store at every step.
    The planner now returns a fully compiled Blockly block tree.
    Raises an exception if any step fails (caller handles fallback).
    """
    # ── Step 1: Semantic Planning + IR Validation + Compilation (inside planner) ──
    job_store.update_step(job_id, "Semantic Planning", "in_progress")
    block_tree = generate_semantic_plan_from_expansion(expansion)

    if isinstance(block_tree, dict) and block_tree.get("error"):
        err_type = block_tree.get("error")
        reason = block_tree.get("reason", "unknown")

        if err_type == "api_key_missing":
            raise RuntimeError("Dynamic Planning needs an API key. Please check your .env file.")
        if err_type == "not_expressible":
            raise RuntimeError("Problem complexity exceeds current strict engine capabilities (falling back).")

        raise RuntimeError(f"Planner error: {err_type} - {reason}")

    if not isinstance(block_tree, dict) or "type" not in block_tree:
        raise RuntimeError("Planner did not return a valid Blockly block tree.")

    job_store.update_step(
        job_id, "Semantic Planning", "completed",
        f"IR validated and compiled to Blockly (root: {block_tree.get('type', 'unknown')})"
    )

    # ── Step 2: IR Validation (already done inside planner — surface result) ─
    job_store.update_step(job_id, "Validation", "in_progress")
    # Lightweight schema check on the compiled Blockly tree
    validator = CapabilityValidator(str(NORMALIZED_BLOCKS))
    # The tree is already compiled, so run block-level check only
    root_type = block_tree.get("type", "")
    if root_type not in {b["type"] for b in validator.blocks}:
        raise RuntimeError(f"Compiled block tree has unknown root type: {root_type}")
    job_store.update_step(job_id, "Validation", "completed", "Block tree schema verified")

    # ── Step 3: Normalization (BlocklyCompiler — ensures all keys present) ───
    job_store.update_step(job_id, "IR Compilation", "in_progress")
    normalizer = BlocklyCompiler()
    block_tree = normalizer.compile(block_tree)

    BLOCK_TREE_OUT.parent.mkdir(parents=True, exist_ok=True)
    BLOCK_TREE_OUT.write_text(json.dumps(block_tree, indent=2), encoding="utf-8")
    job_store.update_step(job_id, "IR Compilation", "completed", "block_tree.json written")

    # ── Step 4: XML Generation ───────────────────────────────────────────────
    job_store.update_step(job_id, "XML Generation", "in_progress")
    node_out = _run_node(ASSEMBLER_DIR)
    xml = _read_xml()
    job_store.update_step(job_id, "XML Generation", "completed", "program.xml generated")

    skeleton = block_tree.get("type", "blockly_tree")
    return xml, block_tree, [
        "Semantic IR validated",
        "IR compiled to Blockly tree",
        "Block tree normalized",
        f"XML generation output: {node_out}",
    ], expansion, skeleton


# ──────────────────────────────────────────────────────────────────────────────
# Fallback path
# ──────────────────────────────────────────────────────────────────────────────

def _run_fallback_pipeline(job_id: str, problem: str, reason: str):
    """
    Triggers the LLM fallback when the strict pipeline fails.
    Returns (xml, ir, logs).
    """
    _log(job_id, f"[FALLBACK] Triggered — reason: {reason}")

    # Mark remaining pending steps as skipped
    job = job_store.get_job(job_id)
    if job:
        for step in job["steps"]:
            if step["status"] == "pending":
                step["status"] = "skipped"
            if step["status"] == "in_progress":
                step["status"] = "failed"
                step["detail"] = reason

    xml, python_code = generate_fallback_outputs(problem)
    ir = {"type": "fallback", "note": "Generated by LLM fallback, no strict IR available"}
    # Post-process XML for common LLM hallucinations
    if xml:
         xml = xml.replace('type="controls_flow"', 'type="controls_flow_statements"')

    logs = [
        f"Strict pipeline failed: {reason}",
        "Fallback LLM invoked",
        "Fallback XML and Python generated",
    ]
    return xml, ir, logs, python_code


# ──────────────────────────────────────────────────────────────────────────────
# Public: run_job (called in a background thread)
# ──────────────────────────────────────────────────────────────────────────────

def run_job(job_id: str, problem: str):
    """
    Executes the pipeline for a single problem.
    Updates job_store throughout so GET /api/status/{job_id} returns live data.
    """
    start_ms = time.time()
    job_store.set_job_in_progress(job_id)

    expansion = problem  # Initialize with original in case expand_problem fails
    try:
        # Pre-expand the problem so we can pass it to both strict and fallback paths
        expansion = expand_problem(problem)
    except Exception as e:
        _log(job_id, f"AI-Expansion skipped: {e}")
        
    try:
        xml, ir, logs, expansion_used, skeleton = _run_strict_pipeline(job_id, expansion)
        elapsed = int((time.time() - start_ms) * 1000)
        job_store.set_job_result(job_id, xml=xml, ir=ir, logs=logs, expansion=expansion_used, skeleton=skeleton)
        job = job_store.get_job(job_id)
        if job:
            job["elapsed_ms"] = elapsed

    except Exception as e:
        reason = str(e)
        try:
            # Pass the expanded problem to the fallback LLM for higher quality output
            xml, ir, logs, python = _run_fallback_pipeline(job_id, expansion, reason)
            elapsed = int((time.time() - start_ms) * 1000)
            job_store.set_job_result(
                job_id, xml=xml, ir=ir, logs=logs,
                python=python,
                expansion=expansion,
                fallback=True, fallback_reason=reason,
            )
            job = job_store.get_job(job_id)
            if job:
                job["elapsed_ms"] = elapsed
        except Exception as fb_err:
            job_store.set_job_failed(job_id, error=f"Fallback also failed: {fb_err}")


def run_job_async(job_id: str, problem: str):
    """Spawns a background thread to run the pipeline without blocking the API."""
    t = threading.Thread(target=run_job, args=(job_id, problem), daemon=True)
    t.start()
