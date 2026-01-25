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
    # Try extracting JSON
    # -------------------------
    try:
        data = extract_json_from_text(raw)

        xml = data.get("xml")
        py = data.get("python")

        if not xml or not py:
            raise ValueError("Missing xml or python")

        return xml, py
    except Exception:
        pass
    
    # -------------------------
    # 2️⃣ Try separating XML + Python from raw text
    # -------------------------
    try:
        xml, py = separate_xml_and_python(raw)
        return xml, py

    except Exception as e:
        # -------------------------
        # LAST RESORT: dump raw text
        # -------------------------
        return (
            "<xml></xml>",
            "# Fallback JSON extraction failed\n"
            "# Raw LLM output below:\n\n"
            + raw
        )
        
       
