"""
Prompt definitions for Semantic Planner (Module 1)

This prompt is designed to produce:
- Semantically correct
- Deterministic
- Minimal
semantic plans (IR format) that the SemanticCompiler translates to Blockly.
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
        "       * 'foreach': Iterate over a list. Fields: var, list, body.\n"
        "       * 'loop_repeat': Iterate from start to end. Fields: var, start, to, body.\n"
        "       * 'while': Repeat while a condition is true. Fields: condition, body.\n"
        "       * 'break' / 'continue': Control flow.\n"
        "       * 'list_op': List operations. Fields: operation (append), list, value.\n"
        "       * 'list_set': Set list[index] = value. Fields: list, index, value.\n"
        "       * 'return': Return a value from the program.\n\n"

        "3) expressions:\n"
        "   - Variable reference: Use the variable name directly as a string (e.g., \"total\").\n"
        "   - Numeric Literal: { \"op\": \"number\", \"value\": 10 }\n"
        "   - String Literal: { \"op\": \"text\", \"value\": \"hello\" }\n"
        "   - Arithmetic: { \"op\": \"+\", \"args\": [left, right] } (valid ops: +, -, *, /, mod).\n"
        "   - Unary math: { \"op\": \"abs\", \"args\": [expr] }\n"
        "   - Min/Max: { \"op\": \"min\", \"args\": [a, b] } or { \"op\": \"max\", \"args\": [a, b] }\n"
        "   - Logic compare: { \"op\": \">\", \"left\": left, \"right\": right } "
        "(valid ops: >, <, >=, <=, ==, !=).\n"
        "   - Logic combine: { \"op\": \"and\", \"args\": [a, b] } or { \"op\": \"or\", \"args\": [a, b] }\n"
        "   - List get: { \"op\": \"list_get\", \"args\": [list_name, 0_based_index] }\n"
        "   - List length: { \"op\": \"len\", \"args\": [list_name] }\n"
        "   - List creation: { \"op\": \"create_list\", \"args\": [a, b, c] }\n\n"

        "IMPORTANT INDEXING RULE:\n"
        "   - Use 0-based indexing in all expressions (e.g., first element = index 0).\n"
        "   - The compiler will automatically convert to 1-based indexing for Blockly.\n\n"

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
        "      \"then\": [ { \"type\": \"print\", \"value\": { \"op\": \"text\", \"value\": \"Big Sum\" } } ],\n"
        "      \"else\": [ { \"type\": \"print\", \"value\": { \"op\": \"text\", \"value\": \"Small Sum\" } } ]\n"
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
        "Generate a semantic plan (IR JSON) for the following problem.\n\n"

        "PROBLEM:\n"
        f"{problem_text}\n\n"

        "Rules:\n"
        "- Output REASONING first, then SEMANTIC PLAN JSON.\n"
        "- The JSON must contain 'inputs' and 'program' keys.\n"
        "- Use 0-based indexing in list_get expressions.\n"
        "- Do NOT output Blockly JSON or Python code.\n"
        "- Return ONLY the semantic IR."
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
        "- Use only the IR vocabulary: assign, foreach, if, list_get, list_op, print.\n"
        "- Output exactly one JSON object (the filled skeleton) and nothing else.\n"
        "If you cannot fill the skeleton validly, output: {\"error\":\"not_expressible\"}.\n"
        "PROBLEM DESCRIPTION:\n"
        f"{problem_text}\n\n"
        "Here is the skeleton:\n"
        f"{skeleton_str}\n"
        "Fill and return JSON only."
    )


# ---------------------------------------------------------------------------
# NEW DIRECT BLOCKLY PROMPT — kept here for reference / future use
# ---------------------------------------------------------------------------
# def system_prompt_blockly_direct() -> str:
#     """
#     Generates Blockly JSON directly without IR intermediary.
#     NOT currently used — the SemanticCompiler IR path is more reliable.
#     """
#     return (
#         "You are a Blockly program generator.\n\n"
#         "Your task is to convert a problem statement into a VALID Blockly JSON tree.\n"
#         "You MUST strictly follow the Blockly schema from the capability summary.\n"
#         ...
#     )
