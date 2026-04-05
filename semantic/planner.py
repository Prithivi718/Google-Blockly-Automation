"""
Semantic Planner (Module 1)

Flow:
  1. Expand problem text
  2. LLM produces Semantic IR JSON (inputs + program)
  3. CapabilityValidator checks IR correctness
  4. SemanticCompiler translates IR → Blockly block tree
  5. BlocklyCompiler normalizes the tree
  6. Returns the final Blockly block tree
"""

import json
import os
from pathlib import Path
from typing import Dict, Union

from dotenv import load_dotenv
from openai import OpenAI

from semantic.prompt import system_prompt, user_prompt, filler_prompt
from semantic.question_expander import expand_problem
from semantic.json_utils import extract_json_from_text
from semantic.schema import SKELETONS
from semantic.block_summary import generate_block_summary
from semantic.validator import CapabilityValidator, CapabilityError
from semantic.compiler import SemanticCompiler, BlocklyCompiler

load_dotenv()


class SemanticPlannerError(Exception):
    pass


def classify_problem(detailed_problem: str) -> str:
    """
    Deterministic rule-based classifier.
    Returns a SKELETON_ID or None.
    """
    text = detailed_problem.lower()

    if "# PROBLEM_TAG: largest_element" in detailed_problem or "largest" in text or "maximum" in text or "biggest" in text:
        return "FOREACH_AGGREGATE"
    if "move zeros" in text or "move zeroes" in text or ("move" in text and "zeros" in text):
        return "MOVE_ZEROS"
    if "rotate" in text and ("array" in text or "list" in text):
        return "INDEX_ROTATION"
    if ("# PROBLEM_TAG: linear_search" in detailed_problem or "linear search" in text) and "subarray" not in text:
        return "LINEAR_SEARCH"

    return None


def generate_semantic_plan_from_expansion(
    detailed_problem: str,
) -> Dict[str, Union[str, list, dict]]:
    """
    Takes an ALREADY EXPANDED problem and:
      1. Calls the LLM to get a Semantic IR JSON.
      2. Validates the IR with CapabilityValidator.
      3. Compiles the IR → Blockly block tree via SemanticCompiler.
      4. Normalizes with BlocklyCompiler.
      5. Returns the final Blockly block tree.
    """
    ROOT = Path(__file__).parent.parent
    blocks_path = str(ROOT / "data" / "normalized_blocks.json")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {
            "error": "api_key_missing",
            "reason": "Dynamic Grounded Planning requires OPENROUTER_API_KEY",
        }

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    # Build validator + compilers once
    validator = CapabilityValidator(blocks_path)
    ir_compiler = SemanticCompiler(validator=None)   # validator applied manually below
    blockly_normalizer = BlocklyCompiler(validator=None)

    print("Mode: Dynamic IR Planning → Compile → Blockly")

    prompt_messages = [
        {"role": "system", "content": system_prompt()},
        {"role": "user",   "content": user_prompt(detailed_problem)},
    ]

    max_retries = 3
    ir_plan = {}

    for attempt in range(max_retries):
        # ── LLM call ────────────────────────────────────────────────────────
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=prompt_messages,
                temperature=0.2 if attempt > 0 else 0,
            )
            raw_output = response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == max_retries - 1:
                raise SemanticPlannerError(
                    f"LLM call failed after {max_retries} attempts: {e}"
                )
            print(f"LLM Error (attempt {attempt + 1}): {e}, retrying...")
            continue

        # ── JSON extraction ──────────────────────────────────────────────────
        try:
            ir_plan = extract_json_from_text(raw_output)
            print(f"IR Plan (attempt {attempt + 1}): {ir_plan}")
        except Exception:
            if attempt == max_retries - 1:
                raise SemanticPlannerError(
                    f"Failed to extract JSON after {max_retries} attempts.\nLast output:\n{raw_output}"
                )
            print(f"JSON extraction failed (attempt {attempt + 1}), retrying...")
            prompt_messages.append({
                "role": "user",
                "content": "Your last response was not valid JSON. Return ONLY the JSON object.",
            })
            continue

        # ── not_expressible passthrough ──────────────────────────────────────
        if isinstance(ir_plan, dict) and ir_plan.get("error") == "not_expressible":
            return ir_plan

        # ── IR Validation ────────────────────────────────────────────────────
        validation = validator.validate(ir_plan)
        if validation["status"] != "ok":
            reason = validation.get("reason", "unknown")
            print(f"IR Validation failed (attempt {attempt + 1}): {reason}")
            if attempt == max_retries - 1:
                raise SemanticPlannerError(
                    f"IR Validation failed after {max_retries} attempts: {reason}"
                )
            prompt_messages.append({
                "role": "user",
                "content": (
                    f"Your semantic plan has a validation error:\n{reason}\n\n"
                    "Fix the plan. Rules:\n"
                    "- Use ONLY allowed step types: assign, print, if, foreach, loop_repeat, while, break, continue, list_op, list_set, return.\n"
                    "- Use ONLY allowed expression ops: number, +, -, *, /, mod, abs, min, max, >, <, >=, <=, ==, !=, and, or, not, list_get, len, create_list, text, to_string, to_number.\n"
                    "- Do NOT use 0-based indexing with len() as an index.\n"
                    "Return ONLY corrected JSON."
                ),
            })
            continue

        # ── IR → Blockly Compilation ─────────────────────────────────────────
        try:
            block_tree = ir_compiler.compile(ir_plan)
        except CapabilityError as e:
            compile_err = str(e)
            print(f"Compilation failed (attempt {attempt + 1}): {compile_err}")
            if attempt == max_retries - 1:
                raise SemanticPlannerError(
                    f"Compilation failed after {max_retries} attempts: {compile_err}"
                )
            prompt_messages.append({
                "role": "user",
                "content": (
                    f"Your semantic plan could not be compiled:\n{compile_err}\n\n"
                    "Fix the plan and return corrected JSON only."
                ),
            })
            continue

        # ── Blockly Normalization ─────────────────────────────────────────────
        try:
            block_tree = blockly_normalizer.compile(block_tree)
        except CapabilityError as e:
            # Normalization errors are internal — surface as planner error
            raise SemanticPlannerError(f"Blockly normalization failed: {e}")

        print("Pipeline: IR validated → compiled → normalized ✓")
        return block_tree

    raise SemanticPlannerError("Planner exhausted all retries without producing a valid plan.")


def generate_semantic_plan(
    problem_text: str,
) -> tuple[Dict[str, Union[str, list, dict]], str]:
    """
    Backward-compatible wrapper.
    Expands the problem and then produces + compiles the semantic plan.
    Returns (block_tree, expansion).
    """
    if not problem_text or not isinstance(problem_text, str):
        raise SemanticPlannerError("Problem text must be a non-empty string")

    # 1. Expand problem
    detailed_problem = expand_problem(problem_text)

    # 2. Plan → Validate IR → Compile → Normalize
    block_tree = generate_semantic_plan_from_expansion(detailed_problem)

    return block_tree, detailed_problem
