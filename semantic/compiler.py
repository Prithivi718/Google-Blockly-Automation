from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Union

from semantic.validator import CapabilityValidator, CapabilityError


BlocklyNode = Dict[str, Any]


# ===========================================================================
# SemanticCompiler — PRIMARY: Translates Old Semantic IR → Blockly block tree
# ===========================================================================

class SemanticCompiler:
    """
    Compiles a semantic IR plan into a Blockly-aligned block tree.

    Input contract:
        A Semantic IR JSON produced by the Planner LLM:
        {
          "inputs":  [ { "name": "A", "type": "list<int>" }, ... ],
          "program": [ { "type": "assign", ... }, ... ]
        }

    Responsibilities:
        - Validate the IR with CapabilityValidator (if provided)
        - Compile inputs → text_prompt / list parser blocks
        - Compile each program step → Blockly block
        - Auto-convert 0-based indices to 1-based (Blockly rule)
        - Chain all blocks via `next` into a single root node
    """

    def __init__(self, validator: Optional[CapabilityValidator] = None):
        self.validator = validator

    # -----------------------------
    # Public API
    # -----------------------------
    def compile(self, plan: Dict) -> BlocklyNode:
        """
        Validate (optional) and compile the IR plan into a Blockly block tree.
        Returns the root Blockly block node.
        """
        if self.validator:
            res = self.validator.validate(plan)
            if res["status"] != "ok":
                raise CapabilityError(
                    f"Compiler Abort: Plan validation failed: {res.get('reason')}"
                )

        head = None
        current = None

        # 1. Inputs — generate variable assignment + prompt blocks
        for inp in plan.get("inputs", []):
            node = self._compile_input(inp)
            head, current = self._chain(head, current, node)

        # 2. Program — compile each IR step into Blockly blocks
        if "program" in plan:
            program_head = self._compile_program(plan["program"])
            head, current = self._chain(head, current, program_head)
        else:
            # Legacy IR fallback: derived + condition + actions
            for drv in plan.get("derived", []):
                node = self._compile_derived(drv)
                head, current = self._chain(head, current, node)

            condition = plan.get("condition")
            if condition and condition.get("conditions"):
                node = self._compile_if(condition, plan.get("actions", {}))
                head, current = self._chain(head, current, node)

        return head

    # -----------------------------
    # Helpers
    # -----------------------------
    def _chain(self, head, current, node):
        """Chain a new block to the end of the current block sequence."""
        if not node:
            return head, current

        if head is None:
            tail = node
            while tail.get("next"):
                tail = tail["next"]
            return node, tail

        current["next"] = node
        tail = node
        while tail.get("next"):
            tail = tail["next"]

        return head, tail

    def _compile_program(self, program: List[Dict]) -> Optional[BlocklyNode]:
        head = None
        current = None

        for step in program:
            node = self._compile_step(step)
            head, current = self._chain(head, current, node)

        return head

    def _to_blockly_index(self, index_expr: Union[int, str, Dict]) -> BlocklyNode:
        """
        Convert a 0-based semantic index to a 1-based Blockly index.
        Result: index + 1
        """
        return {
            "type": "math_arithmetic",
            "fields": {"OP": "ADD"},
            "value_inputs": {
                "A": self._compile_expression(index_expr),
                "B": {"type": "math_number", "fields": {"NUM": "1"}}
            },
            "statement_inputs": {}
        }

    # -----------------------------
    # Step Compilers
    # -----------------------------
    def _compile_step(self, step: Dict) -> Optional[BlocklyNode]:
        step_type = step.get("type")

        if step_type == "assign":
            return {
                "type": "variables_set",
                "fields": {"VAR": step["var"]},
                "value_inputs": {"VALUE": self._compile_expression(step["value"])},
                "statement_inputs": {}
            }

        if step_type == "list_set":
            return {
                "type": "lists_setIndex",
                "fields": {"MODE": "SET", "WHERE": "FROM_START"},
                "value_inputs": {
                    "LIST": self._compile_value(step["list"]),
                    "AT": self._to_blockly_index(step["index"]),
                    "TO": self._compile_expression(step["value"])
                },
                "statement_inputs": {}
            }

        if step_type == "print":
            return {
                "type": "text_print",
                "fields": {},
                "value_inputs": {"TEXT": self._compile_expression(step["value"])},
                "statement_inputs": {}
            }

        if step_type == "if":
            cond_node = self._compile_expression(step["condition"])
            then_block = self._compile_program(step.get("then", []))
            else_block = self._compile_program(step.get("else", []))

            stmt_inputs = {"DO0": then_block} if then_block else {}
            if else_block:
                stmt_inputs["ELSE"] = else_block

            return {
                "type": "controls_if",
                "fields": {},
                "value_inputs": {"IF0": cond_node},
                "statement_inputs": stmt_inputs
            }

        if step_type == "foreach":
            return {
                "type": "controls_forEach",
                "fields": {"VAR": step["var"]},
                "value_inputs": {"LIST": self._compile_expression(step["list"])},
                "statement_inputs": {"DO": self._compile_program(step.get("body", []))},
            }

        if step_type == "loop_repeat":
            start_node = self._compile_expression(step["start"])
            to_node = self._compile_expression(step["to"])

            return {
                "type": "controls_for",
                "fields": {"VAR": step["var"]},
                "value_inputs": {
                    "FROM": start_node,
                    "TO": to_node,
                    "BY": {"type": "math_number", "fields": {"NUM": "1"}}
                },
                "statement_inputs": {"DO": self._compile_program(step.get("body", []))}
            }

        if step_type == "while":
            return {
                "type": "controls_repeat_while",
                "fields": {"MODE": "WHILE"},
                "value_inputs": {"BOOL": self._compile_expression(step["condition"])},
                "statement_inputs": {"DO": self._compile_program(step.get("body", []))}
            }

        if step_type == "break":
            return {
                "type": "controls_flow_statements",
                "fields": {"FLOW": "BREAK"},
                "value_inputs": {},
                "statement_inputs": {}
            }

        if step_type == "continue":
            return {
                "type": "controls_flow_statements",
                "fields": {"FLOW": "CONTINUE"},
                "value_inputs": {},
                "statement_inputs": {}
            }

        if step_type == "list_op":
            operation = step.get("operation")

            if operation == "append":
                # Use lists_append (available in normalized_blocks.json)
                return {
                    "type": "lists_append",
                    "fields": {},
                    "value_inputs": {
                        "LIST": self._compile_value(step["list"]),
                        "ITEM": self._compile_expression(step["value"])
                    },
                    "statement_inputs": {}
                }
            else:
                raise CapabilityError(f"Unsupported list_op operation: {operation}")

        if step_type == "return":
            return {
                "type": "controls_return",
                "fields": {},
                "value_inputs": {"VALUE": self._compile_expression(step["value"])},
                "statement_inputs": {}
            }

        # Unknown step — raise to trigger LLM retry
        raise CapabilityError(f"Unsupported step type: {step_type}")

    # -----------------------------
    # Expression Compilers
    # -----------------------------
    def _compile_expression(self, expr: Union[Dict, str, int, float]) -> BlocklyNode:
        if not isinstance(expr, dict):
            return self._compile_value(expr)

        op = expr.get("op")

        SUPPORTED_OPS = {
            "number", "+", "-", "*", "/", "mod",
            "abs", "min", "max",
            "to_string", "to_number",
            "text", "text_length", "text_getSubstring",
            "list_get", "create_list", "len",
            ">", "<", ">=", "<=", "==", "!=",
            "and", "or", "not"
        }

        if op not in SUPPORTED_OPS:
            raise CapabilityError(f"Unsupported op: {op}")

        if op == "list_get":
            return {
                "type": "lists_getIndex",
                "fields": {"MODE": "GET", "WHERE": "FROM_START"},
                "value_inputs": {
                    "VALUE": self._compile_value(expr["args"][0]),
                    "AT": self._to_blockly_index(expr["args"][1])
                },
                "statement_inputs": {}
            }

        if op == "number":
            return self._compile_value(expr["value"])

        if op == "create_list":
            args = expr.get("args", [])
            value_inputs = {}
            for i, arg in enumerate(args):
                value_inputs[f"ADD{i}"] = self._compile_expression(arg)
            return {
                "type": "lists_create_with",
                "fields": {"ITEMS": str(len(args))},
                "value_inputs": value_inputs,
                "statement_inputs": {}
            }

        if op == "text":
            return {
                "type": "text",
                "fields": {"TEXT": expr["value"]},
                "value_inputs": {},
                "statement_inputs": {}
            }

        if op == "to_string":
            return {
                "type": "text_to_string",
                "fields": {},
                "value_inputs": {"VALUE": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op == "to_number":
            return {
                "type": "text_to_number",
                "fields": {},
                "value_inputs": {"TEXT": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op == "abs":
            return {
                "type": "math_single",
                "fields": {"OP": "ABS"},
                "value_inputs": {"NUM": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op == "text_length":
            return {
                "type": "text_length",
                "fields": {},
                "value_inputs": {"VALUE": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op == "text_getSubstring":
            return {
                "type": "text_getSubstring",
                "fields": {"WHERE1": "FROM_START", "WHERE2": "FROM_START"},
                "value_inputs": {
                    "STRING": self._compile_expression(expr["args"][0]),
                    "AT1": self._compile_expression(expr["args"][1]),
                    "AT2": self._compile_expression(expr["args"][2])
                },
                "statement_inputs": {}
            }

        if op == "len":
            return {
                "type": "lists_length",
                "fields": {},
                "value_inputs": {"VALUE": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op == "not":
            return {
                "type": "logic_negate",
                "fields": {},
                "value_inputs": {"BOOL": self._compile_expression(expr["args"][0])},
                "statement_inputs": {}
            }

        if op in {"+", "-", "*", "/", "mod", "min", "max"}:
            return self._compile_arithmetic(expr)

        if op in {">", "<", ">=", "<=", "==", "!=", "and", "or"}:
            return self._compile_logic_expression(expr)

        raise CapabilityError(f"Unsupported expression op: {op}")

    def _compile_arithmetic(self, expr: Dict) -> BlocklyNode:
        op = expr["op"]

        if op in {"+", "-", "*", "/"}:
            op_map = {"+": "ADD", "-": "MINUS", "*": "MULTIPLY", "/": "DIVIDE"}
            return {
                "type": "math_arithmetic",
                "fields": {"OP": op_map[op]},
                "value_inputs": {
                    "A": self._compile_expression(
                        expr["left"] if "left" in expr else expr["args"][0]
                    ),
                    "B": self._compile_expression(
                        expr["right"] if "right" in expr else expr["args"][1]
                    )
                },
                "statement_inputs": {}
            }

        if op == "mod":
            return {
                "type": "math_modulo",
                "fields": {},
                "value_inputs": {
                    "DIVIDEND": self._compile_expression(expr["args"][0]),
                    "DIVISOR": self._compile_expression(expr["args"][1])
                },
                "statement_inputs": {}
            }

        if op in {"min", "max"}:
            return {
                "type": "math_minmax",
                "fields": {"OP": op.upper()},
                "value_inputs": {
                    "A": self._compile_expression(expr["args"][0]),
                    "B": self._compile_expression(expr["args"][1])
                },
                "statement_inputs": {}
            }

        # Fallback
        return {"type": "math_number", "fields": {"NUM": "0"},
                "value_inputs": {}, "statement_inputs": {}}

    def _compile_logic_expression(self, expr: Dict) -> BlocklyNode:
        op = expr["op"]

        if op in {"and", "or"}:
            return {
                "type": "logic_operation",
                "fields": {"OP": op.upper()},
                "value_inputs": {
                    "A": self._compile_expression(
                        expr["left"] if "left" in expr else expr["args"][0]
                    ),
                    "B": self._compile_expression(
                        expr["right"] if "right" in expr else expr["args"][1]
                    )
                },
                "statement_inputs": {}
            }

        op_map = {
            "==": "EQ", "!=": "NEQ",
            "<": "LT", "<=": "LTE",
            ">": "GT", ">=": "GTE"
        }
        return {
            "type": "logic_compare",
            "fields": {"OP": op_map[op]},
            "value_inputs": {
                "A": self._compile_expression(
                    expr["left"] if "left" in expr else expr["args"][0]
                ),
                "B": self._compile_expression(
                    expr["right"] if "right" in expr else expr["args"][1]
                )
            },
            "statement_inputs": {}
        }

    # -----------------------------
    # Input Compilers
    # -----------------------------
    def _compile_input(self, inp: Dict) -> BlocklyNode:
        if inp["type"] == "list<int>":
            return self._compile_list_input_parser(inp["name"])

        # Prompt for scalar (int / float / string)
        type_field = "NUMBER" if inp["type"] in {"int", "float"} else "TEXT"
        return {
            "type": "variables_set",
            "fields": {"VAR": inp["name"]},
            "value_inputs": {
                "VALUE": {
                    "type": "text_prompt",
                    "fields": {},
                    "value_inputs": {
                        "TEXT": {
                            "type": "text",
                            "fields": {"TEXT": f"Enter {inp['name']}"},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

    def _compile_list_input_parser(self, name: str) -> BlocklyNode:
        """
        Compiles a character-by-character parser for space-separated integers.
        Workaround for the absence of lists_split in the block set.
        """
        raw_var = f"{name}_raw"
        res_var = f"{name}_parsed"
        temp_var = f"{name}_temp"
        idx_var = f"{name}_i"
        char_var = f"{name}_char"

        # 1. raw = prompt(...)
        n1 = {
            "type": "variables_set",
            "fields": {"VAR": raw_var},
            "value_inputs": {
                "VALUE": {
                    "type": "text_prompt",
                    "fields": {},
                    "value_inputs": {
                        "TEXT": {
                            "type": "text",
                            "fields": {"TEXT": f"Enter {name} (space-separated integers)"},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

        # 2. res = []
        n2 = {
            "type": "variables_set",
            "fields": {"VAR": res_var},
            "value_inputs": {
                "VALUE": {
                    "type": "lists_create_with",
                    "fields": {"ITEMS": "0"},
                    "value_inputs": {},
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

        # 3. temp = ""
        n3 = {
            "type": "variables_set",
            "fields": {"VAR": temp_var},
            "value_inputs": {
                "VALUE": {
                    "type": "text",
                    "fields": {"TEXT": ""},
                    "value_inputs": {},
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

        # Loop body — char = raw[idx]
        body_n1 = {
            "type": "variables_set",
            "fields": {"VAR": char_var},
            "value_inputs": {
                "VALUE": {
                    "type": "text_charAt",
                    "fields": {"WHERE": "FROM_START"},
                    "value_inputs": {
                        "VALUE": {
                            "type": "variables_get",
                            "fields": {"VAR": raw_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "AT": {
                            "type": "variables_get",
                            "fields": {"VAR": idx_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

        # if char == " " → if temp != "" → append(int(temp)); temp = ""
        # else → temp += char
        inner_if = {
            "type": "controls_if",
            "fields": {},
            "value_inputs": {
                "IF0": {
                    "type": "logic_compare",
                    "fields": {"OP": "NEQ"},
                    "value_inputs": {
                        "A": {
                            "type": "variables_get",
                            "fields": {"VAR": temp_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "B": {
                            "type": "text",
                            "fields": {"TEXT": ""},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {
                "DO0": {
                    "type": "lists_append",
                    "fields": {},
                    "value_inputs": {
                        "LIST": {
                            "type": "variables_get",
                            "fields": {"VAR": res_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "ITEM": {
                            "type": "math_to_int",
                            "fields": {},
                            "value_inputs": {
                                "VALUE": {
                                    "type": "variables_get",
                                    "fields": {"VAR": temp_var},
                                    "value_inputs": {},
                                    "statement_inputs": {}
                                }
                            },
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {},
                    "next": {
                        "type": "variables_set",
                        "fields": {"VAR": temp_var},
                        "value_inputs": {
                            "VALUE": {
                                "type": "text",
                                "fields": {"TEXT": ""},
                                "value_inputs": {},
                                "statement_inputs": {}
                            }
                        },
                        "statement_inputs": {}
                    }
                }
            }
        }

        space_if = {
            "type": "controls_if",
            "fields": {},
            "value_inputs": {
                "IF0": {
                    "type": "logic_compare",
                    "fields": {"OP": "EQ"},
                    "value_inputs": {
                        "A": {
                            "type": "variables_get",
                            "fields": {"VAR": char_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "B": {
                            "type": "text",
                            "fields": {"TEXT": " "},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {
                "DO0": inner_if,
                "ELSE": {
                    "type": "variables_set",
                    "fields": {"VAR": temp_var},
                    "value_inputs": {
                        "VALUE": {
                            "type": "text_join",
                            "fields": {"ITEMS": "2"},
                            "value_inputs": {
                                "ADD0": {
                                    "type": "variables_get",
                                    "fields": {"VAR": temp_var},
                                    "value_inputs": {},
                                    "statement_inputs": {}
                                },
                                "ADD1": {
                                    "type": "variables_get",
                                    "fields": {"VAR": char_var},
                                    "value_inputs": {},
                                    "statement_inputs": {}
                                }
                            },
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            }
        }

        body_n1["next"] = space_if

        # 4. Loop over characters
        loop = {
            "type": "controls_for",
            "fields": {"VAR": idx_var},
            "value_inputs": {
                "FROM": {
                    "type": "math_number",
                    "fields": {"NUM": "1"},
                    "value_inputs": {},
                    "statement_inputs": {}
                },
                "TO": {
                    "type": "text_length",
                    "fields": {},
                    "value_inputs": {
                        "VALUE": {
                            "type": "variables_get",
                            "fields": {"VAR": raw_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                },
                "BY": {
                    "type": "math_number",
                    "fields": {"NUM": "1"},
                    "value_inputs": {},
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {"DO": body_n1}
        }

        # 5. Final append check (handles trailing token without trailing space)
        final_check = {
            "type": "controls_if",
            "fields": {},
            "value_inputs": {
                "IF0": {
                    "type": "logic_compare",
                    "fields": {"OP": "NEQ"},
                    "value_inputs": {
                        "A": {
                            "type": "variables_get",
                            "fields": {"VAR": temp_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "B": {
                            "type": "text",
                            "fields": {"TEXT": ""},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {
                "DO0": {
                    "type": "lists_append",
                    "fields": {},
                    "value_inputs": {
                        "LIST": {
                            "type": "variables_get",
                            "fields": {"VAR": res_var},
                            "value_inputs": {},
                            "statement_inputs": {}
                        },
                        "ITEM": {
                            "type": "math_to_int",
                            "fields": {},
                            "value_inputs": {
                                "VALUE": {
                                    "type": "variables_get",
                                    "fields": {"VAR": temp_var},
                                    "value_inputs": {},
                                    "statement_inputs": {}
                                }
                            },
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
            }
        }

        # 6. Assign parsed result to real variable name
        final_assign = {
            "type": "variables_set",
            "fields": {"VAR": name},
            "value_inputs": {
                "VALUE": {
                    "type": "variables_get",
                    "fields": {"VAR": res_var},
                    "value_inputs": {},
                    "statement_inputs": {}
                }
            },
            "statement_inputs": {}
        }

        # Chain the sequence: raw → res=[] → temp="" → loop → final_check → assign
        n1["next"] = n2
        n2["next"] = n3
        n3["next"] = loop
        loop["next"] = final_check
        final_check["next"] = final_assign

        return n1

    # -----------------------------
    # Legacy IR helpers
    # -----------------------------
    def _compile_derived(self, drv: Dict) -> BlocklyNode:
        return {
            "type": "variables_set",
            "fields": {"VAR": drv["name"]},
            "value_inputs": {"VALUE": self._compile_expression(drv["expression"])},
            "statement_inputs": {}
        }

    def _compile_if(self, condition: Dict, actions: Dict) -> BlocklyNode:
        return {
            "type": "controls_if",
            "fields": {},
            "value_inputs": {
                "IF0": (
                    self._compile_logic_expression(condition)
                    if "op" in condition
                    else self._compile_expression(condition)
                )
            },
            "statement_inputs": {
                "DO0": self._compile_legacy_actions(actions.get("then", [])),
                "ELSE": self._compile_legacy_actions(actions.get("else", []))
            }
        }

    def _compile_legacy_actions(self, actions) -> Optional[BlocklyNode]:
        head = None
        current = None
        for action in actions:
            if action["type"] == "print":
                node = {
                    "type": "text_print",
                    "fields": {},
                    "value_inputs": {
                        "TEXT": {
                            "type": "text",
                            "fields": {"TEXT": action["value"]},
                            "value_inputs": {},
                            "statement_inputs": {}
                        }
                    },
                    "statement_inputs": {}
                }
                head, current = self._chain(head, current, node)
        return head

    def _compile_value(self, v: Union[str, int, float]) -> BlocklyNode:
        if isinstance(v, (int, float)):
            return {
                "type": "math_number",
                "fields": {"NUM": str(v)},
                "value_inputs": {},
                "statement_inputs": {}
            }
        return {
            "type": "variables_get",
            "fields": {"VAR": str(v)},
            "value_inputs": {},
            "statement_inputs": {}
        }


# ===========================================================================
# BlocklyCompiler — SECONDARY: Normalizes/validates a raw Blockly block tree
# (used after SemanticCompiler outputs, or when tree arrives pre-built)
# ===========================================================================

class BlocklyCompiler:
    """
    Blockly-only normalizer.

    Input contract:
        A Blockly JSON tree — either from SemanticCompiler output or directly.

    Responsibilities:
        - Validate the tree with CapabilityValidator (optional)
        - Ensure every block has 'fields', 'value_inputs', 'statement_inputs', 'next'
        - Reject old semantic IR wrappers (inputs, program, derived, etc.)
    """

    def __init__(self, validator: Optional[CapabilityValidator] = None):
        self.validator = validator

    def compile(self, plan: Union[BlocklyNode, List[BlocklyNode]]) -> BlocklyNode:
        normalized_plan = self._prepare_root(plan)

        if self.validator:
            res = self.validator.validate(normalized_plan)
            if res.get("status") != "ok":
                raise CapabilityError(
                    f"Compiler Abort: Blockly validation failed: {res.get('reason')}"
                )

        return self._normalize_tree(normalized_plan)

    def _prepare_root(self, plan: Union[BlocklyNode, List[BlocklyNode]]) -> BlocklyNode:
        if isinstance(plan, list):
            if not plan:
                raise CapabilityError("root_empty_list")

            root = deepcopy(plan[0])
            current = root

            for node in plan[1:]:
                if not isinstance(node, dict):
                    raise CapabilityError("invalid_root_block_in_list")
                current["next"] = deepcopy(node)
                current = current["next"]
                while isinstance(current.get("next"), dict):
                    current = current["next"]

            return root

        if not isinstance(plan, dict):
            raise CapabilityError("root_must_be_object")

        # Reject old semantic IR wrappers
        forbidden_wrappers = {"program", "inputs", "derived", "condition", "actions"}
        if any(k in plan for k in forbidden_wrappers):
            raise CapabilityError("semantic_ir_not_supported_in_blockly_normalizer")

        return deepcopy(plan)

    def _normalize_tree(self, node: Any) -> Any:
        if node is None:
            return None

        if isinstance(node, list):
            return [self._normalize_tree(item) for item in node]

        if not isinstance(node, dict):
            return deepcopy(node)

        normalized = deepcopy(node)

        if "fields" not in normalized or normalized["fields"] is None:
            normalized["fields"] = {}
        if "value_inputs" not in normalized or normalized["value_inputs"] is None:
            normalized["value_inputs"] = {}
        if "statement_inputs" not in normalized or normalized["statement_inputs"] is None:
            normalized["statement_inputs"] = {}

        if not isinstance(normalized["fields"], dict):
            raise CapabilityError("invalid_fields_structure")
        if not isinstance(normalized["value_inputs"], dict):
            raise CapabilityError("invalid_value_inputs_structure")
        if not isinstance(normalized["statement_inputs"], dict):
            raise CapabilityError("invalid_statement_inputs_structure")

        for slot, child in list(normalized["value_inputs"].items()):
            normalized["value_inputs"][slot] = self._normalize_tree(child)

        for slot, child in list(normalized["statement_inputs"].items()):
            normalized["statement_inputs"][slot] = self._normalize_tree(child)

        if "next" in normalized and normalized["next"] is not None:
            normalized["next"] = self._normalize_tree(normalized["next"])

        return normalized


# Backward-compatible alias
SemanticCompiler = SemanticCompiler
