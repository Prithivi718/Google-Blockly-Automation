import re


class SeparationError(Exception):
    pass


def separate_xml_and_python(raw: str):
    """
    Separates Blockly-like XML and Python code from an LLM response.

    Returns:
        (xml_str, python_str)
    """

    if not raw or not raw.strip():
        raise SeparationError("Empty LLM response")

    text = raw.strip()

    # ----------------------------------------
    # 1️⃣ Extract XML using structural markers
    # ----------------------------------------
    xml = None
    xml_match = re.search(
        r"(<xml[\s\S]*?</xml>)",
        text,
        re.IGNORECASE
    )

    if xml_match:
        xml = xml_match.group(1)
        text = text.replace(xml, "").strip()

    # ----------------------------------------
    # 2️⃣ Clean markdown fences if present
    # ----------------------------------------
    text = re.sub(r"```(?:python|py)?", "", text)
    text = re.sub(r"```", "", text)

    # ----------------------------------------
    # 3️⃣ Extract Python (heuristic-based)
    # ----------------------------------------
    python_lines = []
    for line in text.splitlines():
        stripped = line.strip()

        # Skip obvious non-code lines
        if not stripped:
            python_lines.append(line)
            continue

        if stripped.startswith((
            "def ",
            "if ",
            "else",
            "elif ",
            "for ",
            "while ",
            "print",
            "return",
            "import ",
            "from ",
        )) or "=" in stripped or stripped.endswith(":"):
            python_lines.append(line)
            continue

        # Also allow function call lines
        if re.match(r"[a-zA-Z_][a-zA-Z0-9_]*\(\)", stripped):
            python_lines.append(line)
            continue

    python_code = "\n".join(python_lines).strip()

    # ----------------------------------------
    # 4️⃣ Final guards
    # ----------------------------------------
    if not xml:
        raise SeparationError("XML not found in LLM response")

    if not python_code:
        raise SeparationError("Python code not found in LLM response")

    return xml, python_code