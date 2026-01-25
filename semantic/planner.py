"""
Semantic Planner (Module 1)

- Calls the LLM
- Produces a STRICT semantic plan JSON
- Does NOT validate feasibility or correctness
"""

import json
import os
from typing import Dict, Union

from dotenv import load_dotenv
from openai import OpenAI

from semantic.prompt import system_prompt, user_prompt, filler_prompt
from semantic.question_expander import expand_problem
from semantic.json_utils import extract_json_from_text
from semantic.schema import SKELETONS

load_dotenv()


class SemanticPlannerError(Exception):
    pass


def classify_problem(detailed_problem: str) -> str:
    """
    Deterministic rule-based classifier.
    Returns a SKELETON_ID or None.
    """
    text = detailed_problem.lower()
    
    # Heuristics
    if "# PROBLEM_TAG: largest_element" in detailed_problem or "largest" in text or "maximum" in text or "biggest" in text:
        return "FOREACH_AGGREGATE"
    if "move zeros" in text or "move zeroes" in text:
        return "MOVE_ZEROS"
    if "rotate" in text and ("array" in text or "list" in text):
        return "INDEX_ROTATION"
    if "# PROBLEM_TAG: linear_search" in detailed_problem or "linear search" in text:
        return "LINEAR_SEARCH"
        
    return None


def generate_semantic_plan(problem_text: str) -> Dict[str, Union[str, list, dict]]:
    if not problem_text or not isinstance(problem_text, str):
        raise SemanticPlannerError("Problem text must be a non-empty string")

    # 1. Expand problem (adding tags if possible)
    detailed_problem = expand_problem(problem_text)

    # 2. Deterministic Classifier
    skeleton_id = classify_problem(detailed_problem)
    
    if not skeleton_id:
        return {"error": "not_expressible", "reason": "no_skeleton_match"}

    skeleton = SKELETONS.get(skeleton_id)
    if not skeleton:
        return {"error": "not_expressible", "reason": f"unknown_skeleton_{skeleton_id}"}

    # 3. Call LLM to fill slots
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SemanticPlannerError("OPENROUTER_API_KEY not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a precise JSON skeleton filler."},
                    {"role": "user", "content": filler_prompt(skeleton, detailed_problem)}
                ],
                temperature=0.2 if attempt > 0 else 0
            )
            
            raw_output = response.choices[0].message.content.strip()
            
            try:
                parsed = extract_json_from_text(raw_output)
                print(f"Filled Skeleton ({skeleton_id}): {parsed}")
                break
            except Exception:
                if attempt == max_retries - 1:
                    raise SemanticPlannerError(f"Failed to extract JSON after {max_retries} attempts. Last output:\n{raw_output}")
                print(f"JSON extraction failed (attempt {attempt+1}), retrying...")
                continue
                
        except Exception as e:
            if attempt == max_retries - 1:
                raise SemanticPlannerError(f"LLM call failed after {max_retries} attempts: {e}")
            print(f"LLM Error (attempt {attempt+1}): {e}, retrying...")

    # Explicit not_expressible passthrough
    if isinstance(parsed, dict) and parsed.get("error") == "not_expressible":
        return parsed

    if not isinstance(parsed, dict):
        raise SemanticPlannerError("Semantic plan must be a JSON object")

    return parsed
