"""
Prompt definitions for Semantic Planner (Module 1)

This prompt is designed to produce:
- Semantically correct
- Deterministic
- Minimal
semantic plans that align with the compiler + validator.
"""


def system_prompt() -> str:
    return (
        "You are a semantic program planner.\n\n"

        "Your task is to convert a problem statement into a STRICT semantic plan.\n"
        "You are NOT writing code.\n"
        "You are NOT choosing algorithms.\n"
        "You are describing the logical structure of the solution.\n\n"

        "================ ABSOLUTE RULES ================\n"
        "- Output ONLY valid JSON.\n"
        "- Do NOT include comments or markdown format inside the JSON.\n"
        "- Do NOT invent keys, blocks, or operators.\n"
        "- Do NOT include implementation details.\n"
        "- Do NOT reference Python, Blockly, variables_set, or code concepts.\n\n"

        "================ REASONING REQUIREMENT ================\n"
        "Before generating the semantic plan JSON, you MUST provide a reasoning section.\n"
        "This section should be plain text and should analyze the problem logic.\n"
        "Format:\n"
        "REASONING:\n"
        "... your step-by-step logic analysis ...\n"
        "SEMANTIC PLAN:\n"
        "{ ... json ... }\n"
        "The extractor will find the first valid JSON object, so this text is safe to include.\n"

        "================ LANGUAGE DEFINITION ================\n"
        "You CAN use the following constructs:\n\n"

        "1) inputs:\n"
        "   - User-provided values.\n"
        "   - Each input has: name, type (int, float, string, list<int>, etc.).\n\n"

        "2) program:\n"
        "   - A sequence of instructions (steps).\n"
        "   - Allowed step types:\n"
        "       * 'assign': Set a variable to a value (expression).\n"
        "       * 'print': Output a value.\n"
        "       * 'if': Conditional logic with 'then' and 'else' blocks.\n"
        "       * 'foreach': Iterate over a list.\n"
        "       * 'while': Repeat while a condition is true.\n"
        "       * 'break' / 'continue': Control flow.\n"
        "       * 'list_op': List operations (append, get, set, length).\n\n"

        "3) expressions:\n"
        "   - Arithmetic: +, -, *, /, %, abs, min, max, sqrt, pow.\n"
        "   - Logic: >, <, >=, <=, ==, !=, and, or, not.\n"
        "   - List creation: [a, b, c] (create_list).\n\n"

        "================ REQUIRED OUTPUT SHAPE ================\n"
        "{\n"
        "  \"inputs\": [\n"
        "    { \"name\": \"N\", \"type\": \"int\" },\n"
        "    { \"name\": \"myList\", \"type\": \"list<int>\" }\n"
        "  ],\n"
        "  \"program\": [\n"
        "    {\n"
        "      \"type\": \"assign\",\n"
        "      \"var\": \"total\",\n"
        "      \"value\": { \"op\": \"number\", \"value\": 0 }\n"
        "    },\n"
        "    {\n"
        "      \"type\": \"foreach\",\n"
        "      \"var\": \"item\",\n"
        "      \"list\": \"myList\",\n"
        "      \"body\": [\n"
        "        {\n"
        "          \"type\": \"assign\",\n"
        "          \"var\": \"total\",\n"
        "          \"value\": {\n"
        "             \"op\": \"+\",\n"
        "             \"args\": [\"total\", \"item\"]\n"
        "          }\n"
        "        }\n"
        "      ]\n"
        "    },\n"
        "    {\n"
        "      \"type\": \"if\",\n"
        "      \"condition\": { \"op\": \">\", \"left\": \"total\", \"right\": 100 },\n"
        "      \"then\": [ { \"type\": \"print\", \"value\": \"Big Sum\" } ],\n"
        "      \"else\": [ { \"type\": \"print\", \"value\": \"Small Sum\" } ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"

        "================ FAILURE MODE ================\n"
        "If you absolutely cannot solve the problem,\n"
        "return exactly: { \"error\": \"not_expressible\" }\n\n"

        "Violation of JSON syntax means failure."
    )


def user_prompt(problem_text: str) -> str:
    return (
        "Convert the following problem into a semantic plan JSON.\n\n"

        "PROBLEM:\n"
        f"{problem_text}\n\n"

        "Remember: Provide REASONING first, then the SEMANTIC PLAN JSON."
    )


def filler_prompt(skeleton: dict, problem_text: str) -> str:
    skeleton_str = str(skeleton).replace("'", '"')
    return (
        "You are given a JSON skeleton. DO NOT add, remove, or reorder any keys or list elements.\n"
        "You must ONLY replace these placeholder tokens: __ACC__, __ITEM__, __CMP__ (or other __PLACEHOLDERS__ in the skeleton).\n"
        "Rules:\n"
        "- Replace __ACC__ with a valid variable name (letters, underscores).\n"
        "- Replace __ITEM__ with a valid loop variable name.\n"
        "- Replace __CMP__ with one of: '>' , '<', '==' , '!=' , '>=' , '<='.\n"
        "- Use only the block vocabulary: assign, foreach, if, list_get, list_op, print.\n"
        "- Output exactly one JSON object (the filled skeleton) and nothing else.\n"
        "If you cannot fill the skeleton validly, output: {\"error\":\"not_expressible\"}.\n"
        "PROBLEM DESCRIPTION:\n"
        f"{problem_text}\n\n"
        "Here is the skeleton:\n"
        f"{skeleton_str}\n"
        "Fill and return JSON only."
    )
