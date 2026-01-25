import json
import re
from typing import Any, Dict


class JSONExtractionError(Exception):
    pass


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Extracts the first valid JSON object from an arbitrary LLM response.

    Strategy (in order):
    1) Direct JSON parse
    2) Markdown ```json block extraction
    3) Brace-balanced scanning for JSON object

    Raises JSONExtractionError if no valid JSON object is found.
    """

    if not text or not isinstance(text, str):
        raise JSONExtractionError("Input must be a non-empty string")

    text = text.strip()

    # --------------------------------------------------
    # 1) Try direct JSON parse
    # --------------------------------------------------
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    # --------------------------------------------------
    # 2) Extract from ```json ... ``` blocks
    # --------------------------------------------------
    codeblock_pattern = re.compile(
        r"```(?:json)?\s*(\{.*?\})\s*```",
        re.DOTALL
    )

    for match in codeblock_pattern.findall(text):
        try:
            parsed = json.loads(match)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            continue

    # --------------------------------------------------
    # 3) Brace-balanced JSON object extraction
    # --------------------------------------------------
    start = None
    depth = 0

    for i, ch in enumerate(text):
        if ch == "{":
            if start is None:
                start = i
                depth = 1
            else:
                depth += 1
        elif ch == "}":
            if start is not None:
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        start = None
                        depth = 0

    # --------------------------------------------------
    # 4) LAST-RESORT: Salvage partial JSON (fallback only)
    # --------------------------------------------------
    if '"xml"' in text and '"python"' in text:
        try:
            # Heuristic: cut until last closing brace
            last_brace = text.rfind("}")
            if last_brace != -1:
                candidate = text[: last_brace + 1]
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
        except Exception:
            pass

    # --------------------------------------------------
    # Failure
    # --------------------------------------------------
    raise JSONExtractionError(
        "No valid JSON object found in LLM response.\n"
        f"Raw response:\n{text}"
    )
