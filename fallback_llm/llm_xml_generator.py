import os
from dotenv import load_dotenv
from openai import OpenAI

from semantic.json_utils import extract_json_from_text
from fallback_llm.separate_xml_python import separate_xml_and_python
load_dotenv()

class FallbackGenerationError(Exception):
    pass

def system_prompt() -> str:
    return (
        "You are a fallback code generator for a Blockly-based programming platform.\n\n"

        "Your task:\n"
        "- Generate Blockly-like XML that resembles real Blockly structure.\n"
        "- Generate FULLY CORRECT and EXECUTABLE Python code that solves the problem.\n\n"

        "PYTHON REQUIREMENTS (STRICT):\n"
        "1) You MAY define helper functions.\n"
        "2) If you define a function, it MUST be CALLED.\n"
        "3) The program MUST read input from standard input.\n"
        "4) The program MUST produce output using print().\n"
        "5) Do NOT leave logic inside an uncalled function.\n"
        "6) Keep the logic simple and direct.\n\n"

        "XML REQUIREMENTS (BLOCKLY-LIKE, RELAXED):\n"
        "- XML MUST look like Blockly XML.\n"
        "- Use <xml>, <block>, <field>, <value>, <statement> tags.\n"
        "- Use realistic Blockly block types (e.g., logic_compare, math_arithmetic, variables_get, variables_set, controls_if, text_print).\n"
        "- XML does NOT need to be executable or complete.\n"
        "- XML must represent the SAME logic as the Python code at a high level.\n\n"

        "OUTPUT FORMAT (ABSOLUTE RULES):\n"
        "1) Output ONLY a single JSON object.\n"
        "2) The JSON object MUST contain exactly two string fields:\n"
        "   - \"xml\"\n"
        "   - \"python\"\n"
        "3) Do NOT include explanations, markdown, or comments outside code.\n"
        "4) Do NOT include any text outside the JSON object.\n"
    )
    
def user_prompt(problem_text: str) -> str:
    return (
        "Generate Blockly-like XML and executable Python code for the following problem.\n"
        "Ensure the Python code runs fully when executed.\n\n"
        f"{problem_text}"
    )


def _is_valid_xml(xml_str: str) -> bool:
    """Basic check for Blockly-style XML."""
    if not xml_str:
        return False
    return "<xml" in xml_str.lower() and "</xml>" in xml_str.lower()


def _is_valid_python(py_str: str) -> bool:
    """Basic check for non-empty Python code."""
    if not py_str:
        return False
    return len(py_str.strip()) > 5  # arbitrary minimal length

def generate_fallback_outputs(problem_text: str):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        # Absolute last-resort fallback
        return (
            "<xml></xml>",
            "# Fallback failed: API key missing\n"
        )

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            model="qwen/qwen-2.5-7b-instruct",
            # model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_prompt(problem_text)}
            ],
            temperature=0,
            max_tokens=1200
        )

        raw = response.choices[0].message.content

    except Exception as e:
        return (
            "<xml></xml>",
            f"# LLM call failed\n# {e}\n"
        )

    # -------------------------
    # HARD GUARDS (IMPORTANT)
    # -------------------------
    if not raw or not raw.strip():
        return (
            "<xml></xml>",
            "# Empty LLM response in fallback\n"
        )

    # -------------------------
    # Log raw response
    # -------------------------
    print(f"\n--- [FALLBACK RAW RESPONSE] ---\n{raw}\n--- [END RAW] ---\n")

    # -------------------------
    # 1. Try strict JSON parse
    # -------------------------
    import json
    try:
        data = json.loads(raw.strip())
        xml  = data.get("xml", "")
        py   = data.get("python", "")

        if _is_valid_xml(xml) and _is_valid_python(py):
            print("[FALLBACK] Strategy: Strict JSON parse successful.")
            return xml, py
        else:
            print("[FALLBACK] Strict JSON parse success, but validation failed.")
    except Exception as e:
        print(f"[FALLBACK] Strict JSON parse failed: {e}")

    # -------------------------
    # 2. Try heuristic extraction (fallback)
    # -------------------------
    print("[FALLBACK] Attempting heuristic extraction...")
    try:
        data = extract_json_from_text(raw)
        xml  = data.get("xml", "")
        py   = data.get("python", "")

        if _is_valid_xml(xml) and _is_valid_python(py):
            print("[FALLBACK] Strategy: Partial JSON extraction successful.")
            return xml, py
    except Exception as e:
        print(f"[FALLBACK] Partial JSON extraction failed: {e}")

    # -------------------------
    # 3. Final heuristic separation (last resort)
    # -------------------------
    try:
        xml, py = separate_xml_and_python(raw)
        if _is_valid_xml(xml) and _is_valid_python(py):
            print("[FALLBACK] Strategy: Heuristic regex separation successful.")
            return xml, py
    except Exception as e:
        print(f"[FALLBACK] Heuristic separation failed: {e}")

    # -------------------------
    # FAILURE
    # -------------------------
    print("[FALLBACK] CRITICAL: All parsing strategies failed.")
    return (
        "<xml></xml>",
        "# Fallback Error: LLM returned invalid or empty code.\n"
        "# Please check the logs."
    )
        
       
