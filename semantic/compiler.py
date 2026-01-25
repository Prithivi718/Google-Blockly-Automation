from typing import Dict, List, Union
from semantic.validator import CapabilityValidator, CapabilityError

class SemanticCompiler:
    """
    Compiles a semantic plan into a Blockly-aligned block tree.
    Enforces failure on invalid IR.
    """
    
    def __init__(self, validator: CapabilityValidator = None):
        self.validator = validator

    # -----------------------------
    # Public API
    # -----------------------------
    def compile(self, plan: Dict) -> Dict:
        # Pre-compilation validation check
        if self.validator:
             res = self.validator.validate(plan)
             if res["status"] != "ok":
                 raise CapabilityError(f"Compiler Abort: Plan validation failed: {res.get('reason')}")

        head = None
        current = None

        # 1️⃣ Inputs
        for inp in plan.get("inputs", []):
            node = self._compile_input(inp)
            head, current = self._chain(head, current, node)

        # 2️⃣ Program
        if "program" in plan:
            program_head = self._compile_program(plan["program"])
            head, current = self._chain(head, current, program_head)
        
        else:
             # Fallback
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

    def _compile_program(self, program: List[Dict]) -> Dict:
        head = None
        current = None
        
        for step in program:
            node = self._compile_step(step)
            head, current = self._chain(head, current, node)
            
        return head

    def _to_blockly_index(self, index_expr: Union[int, str, Dict]) -> Dict:
        """
        Convert 0-based semantic index to 1-based Blockly index.
        index + 1
        """
        return {
            "type": "math_arithmetic",
            "fields": { "OP": "ADD" },
            "value_inputs": {
                "A": self._compile_expression(index_expr),
                "B": { "type": "math_number", "fields": { "NUM": "1" } }
            }
        }

    def _compile_step(self, step: Dict) -> Dict:
        step_type = step["type"]
        
        if step_type == "assign":
            # Assigning to a variable
            return {
                "type": "variables_set",
                "fields": { "VAR": step["var"] },
                "value_inputs": { "VALUE": self._compile_expression(step["value"]) }
            }

        if step_type == "list_set":
            # Assigning to a list index
            # lists_setIndex -> SET, LIST, AT (FROM_START), TO
            return {
                "type": "lists_setIndex",
                "fields": {
                    "MODE": "SET",
                    "WHERE": "FROM_START" 
                },
                "value_inputs": {
                    "LIST": self._compile_value(step["list"]),
                    "AT": self._to_blockly_index(step["index"]),
                    "TO": self._compile_expression(step["value"])
                }
            }
            
        if step_type == "print":
            val = step["value"]
            if isinstance(val, str) and val not in ["__ACC__", "__ITEM__"]: # simplistic heuristic, ideally value is expression
                 # If it looks like a variable name, use variables_get, else text? 
                 # The validation prompt says "value": "string".
                 # But in skeleton it says "value": "__ACC__".
                 # We'll try to compile as expression first.
                 val_node = self._compile_expression(val)
            else:
                 val_node = self._compile_expression(val)

            return {
                "type": "text_print",
                "value_inputs": { "TEXT": val_node }
            }
            
        if step_type == "if":
             cond_node = self._compile_expression(step["condition"])
             return {
                "type": "controls_if",
                "value_inputs": { "IF0": cond_node },
                "statement_inputs": {
                    "DO0": self._compile_program(step.get("then", [])),
                    "ELSE": self._compile_program(step.get("else", []))
                }
            }
            
        if step_type == "foreach":
            return {
                "type": "controls_forEach",
                "fields": { "VAR": step["var"] },
                "value_inputs": { "LIST": self._compile_value(step["list"]) },
                "statement_inputs": { "DO": self._compile_program(step.get("body", [])) }
            }
            
        if step_type == "loop_repeat":
            # For loop from START to TO
            # Check if start/to are expressions
            start_node = self._compile_expression(step["start"])
            to_node = self._compile_expression(step["to"])
            
            return {
                "type": "controls_for",
                "fields": { "VAR": step["var"] },
                "value_inputs": {
                     "FROM": start_node,
                     "TO": to_node,
                     "BY": { "type": "math_number", "fields": { "NUM": "1" } }
                },
                "statement_inputs": { "DO": self._compile_program(step.get("body", [])) }
            }

        if step_type == "while":
            return {
                "type": "controls_whileUntil",
                "fields": { "MODE": "WHILE" },
                "value_inputs": { "BOOL": self._compile_expression(step["condition"]) },
                "statement_inputs": { "DO": self._compile_program(step.get("body", [])) }
            }

        if step_type == "break":
             return {
                 "type": "controls_flow_statements",
                 "fields": { "FLOW": "BREAK" }
             }
            
        return None

    # -----------------------------
    # Expressions
    # -----------------------------
    def _compile_expression(self, expr: Union[Dict, str, int, float]) -> Dict:
        if not isinstance(expr, dict):
            return self._compile_value(expr)
            
        op = expr.get("op")
        
        if op == "list_get":
            # lists_getIndex -> GET, LIST, AT (FROM_START)
            return {
                "type": "lists_getIndex",
                "fields": {
                    "MODE": "GET",
                    "WHERE": "FROM_START"
                },
                "value_inputs": {
                    "VALUE": self._compile_value(expr["args"][0]), # The list
                    "AT": self._to_blockly_index(expr["args"][1])   # The index
                }
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
                "extraState": { "itemCount": len(args) },
                "value_inputs": value_inputs
            }

        if op == "len":
             return { "type": "lists_length", "value_inputs": { "VALUE": self._compile_expression(expr["args"][0]) } }

        if op in {"+", "-", "*", "/", "mod", "min", "max",  "to_string", "to_number", "abs"}:
            return self._compile_legacy_expression(expr)

        if op in {">", "<", ">=", "<=", "==", "!=", "and", "or"}:
             return self._compile_logic_expression(expr)

        return self._compile_value(str(expr)) 

    def _compile_logic_expression(self, expr: Dict) -> Dict:
        op = expr["op"]
        
        if op in {"and", "or"}:
            return {
                "type": "logic_operation",
                "fields": { "OP": op.upper() },
                "value_inputs": {
                    "A": self._compile_expression(expr.get("left") or expr["args"][0]),
                    "B": self._compile_expression(expr.get("right") or expr["args"][1])
                }
            }
            
        op_map = {
            "==": "EQ", "!=": "NEQ",
            "<": "LT", "<=": "LTE",
            ">": "GT", ">=": "GTE"
        }
        return {
            "type": "logic_compare",
            "fields": { "OP": op_map[op] },
            "value_inputs": {
                "A": self._compile_expression(expr.get("left") or expr["args"][0]),
                "B": self._compile_expression(expr.get("right") or expr["args"][1])
            }
        }

    def _compile_legacy_expression(self, expr: Dict) -> Dict:
        op = expr["op"]
        if op in {"+", "-", "*", "/"}:
            op_map = { "+": "ADD", "-": "MINUS", "*": "MULTIPLY", "/": "DIVIDE" }
            return {
                "type": "math_arithmetic",
                "fields": { "OP": op_map[op] },
                "value_inputs": {
                    "A": self._compile_expression(expr.get("left") or expr["args"][0]),
                    "B": self._compile_expression(expr.get("right") or expr["args"][1])
                }
            }
        if op == "mod":
             # math_modulo
             return {
                 "type": "math_modulo",
                 "value_inputs": {
                     "DIVIDEND": self._compile_expression(expr["args"][0]),
                     "DIVISOR": self._compile_expression(expr["args"][1])
                 }
             }

        # Fallback
        return { "type": "math_number", "fields": { "NUM": "0" } }

    def _compile_input(self, inp: Dict) -> Dict:
        if inp["type"] == "list<int>":
             return self._compile_list_input_parser(inp["name"])

        # Prompt for number if int/float
        type_field = "NUMBER" if inp["type"] in {"int", "float"} else "TEXT" 
        return {
            "type": "variables_set",
            "fields": { "VAR": inp["name"] },
            "value_inputs": {
                "VALUE": {
                    "type": "text_prompt_ext",
                    "fields": { "TYPE": type_field, "TEXT": f"Enter {inp['name']}" }
                }
            }
        }

    def _compile_list_input_parser(self, name: str) -> Dict:
        """
        Manually compiles a parser for space-separated integers.
        workaround for missing lists_split.
        """
        raw_var = f"{name}_raw"
        res_var = f"{name}_parsed"
        temp_var = f"{name}_temp"
        idx_var = f"{name}_i"
        char_var = f"{name}_char"

        # 1. raw = prompt
        n1 = {
            "type": "variables_set",
            "fields": { "VAR": raw_var },
            "value_inputs": {
                "VALUE": {
                    "type": "text_prompt_ext",
                    "fields": { "TYPE": "TEXT", "TEXT": f"Enter {name} (space separated integers)" }
                }
            }
        }

        # 2. res = []
        n2 = {
            "type": "variables_set",
            "fields": { "VAR": res_var },
            "value_inputs": {
                "VALUE": {
                    "type": "lists_create_with",
                    "mutation": { "items": "0" }
                }
            }
        }

        # 3. temp = ""
        n3 = {
            "type": "variables_set",
            "fields": { "VAR": temp_var },
            "value_inputs": {
                "VALUE": {
                    "type": "text",
                    "fields": { "TEXT": "" }
                }
            }
        }

        # 4. Loop
        # Loop body construction
        # char = raw[idx]
        body_n1 = {
            "type": "variables_set",
            "fields": { "VAR": char_var },
            "value_inputs": {
                "VALUE": {
                    "type": "text_charAt",
                    "fields": { "WHERE": "FROM_START" },
                    "value_inputs": {
                        "VALUE": { "type": "variables_get", "fields": { "VAR": raw_var } },
                        "AT": { "type": "variables_get", "fields": { "VAR": idx_var } }
                    }
                }
            }
        }

        # If char == " "
        append_if = {
            "type": "controls_if",
            "value_inputs": {
                "IF0": {
                    "type": "logic_compare", 
                    "fields": { "OP": "EQ" },
                    "value_inputs": {
                        "A": { "type": "variables_get", "fields": { "VAR": char_var } },
                        "B": { "type": "text", "fields": { "TEXT": " " } }
                    }
                }
            },
            "statement_inputs": {
                "DO0": {
                    # Inner If temp != ""
                    "type": "controls_if",
                    "value_inputs": {
                         "IF0": {
                            "type": "logic_compare", 
                            "fields": { "OP": "NEQ" },
                            "value_inputs": {
                                "A": { "type": "variables_get", "fields": { "VAR": temp_var } },
                                "B": { "type": "text", "fields": { "TEXT": "" } }
                            }
                         }
                    },
                    "statement_inputs": {
                        # append(int(temp))
                        "DO0": {
                            "type": "lists_setIndex",
                            "fields": { "MODE": "INSERT", "WHERE": "LAST" },
                            "value_inputs": {
                                "LIST": { "type": "variables_get", "fields": { "VAR": res_var } },
                                "TO": {
                                    "type": "math_to_int",
                                    "value_inputs": {
                                        "VALUE": { "type": "variables_get", "fields": { "VAR": temp_var } }
                                    }
                                }
                            },
                            # temp = ""
                            "next": {
                                "type": "variables_set",
                                "fields": { "VAR": temp_var },
                                "value_inputs": { "VALUE": { "type": "text", "fields": { "TEXT": "" } } }
                            }
                        }
                    }
                },
                "ELSE": {
                    # temp += char
                     "type": "variables_set",
                     "fields": { "VAR": temp_var },
                     "value_inputs": {
                         "VALUE": {
                             "type": "text_join",
                             "fields": { "ITEMS": "2" },
                             "value_inputs": {
                                 "ADD0": { "type": "variables_get", "fields": { "VAR": temp_var } },
                                 "ADD1": { "type": "variables_get", "fields": { "VAR": char_var } }
                             }
                         }
                     }
                }
            }
        }
        
        body_n1["next"] = append_if

        loop = {
            "type": "controls_for",
            "fields": { "VAR": idx_var },
            "value_inputs": {
                "FROM": { "type": "math_number", "fields": { "NUM": "1" } },
                "TO": {
                    "type": "text_length",
                    "value_inputs": {
                         "VALUE": { "type": "variables_get", "fields": { "VAR": raw_var } }
                    }
                },
                "BY": { "type": "math_number", "fields": { "NUM": "1" } }
            },
            "statement_inputs": {
                "DO": body_n1
            }
        }
        
        # 5. Final append check
        final_check = {
            "type": "controls_if",
            "value_inputs": {
                 "IF0": {
                    "type": "logic_compare", 
                    "fields": { "OP": "NEQ" },
                    "value_inputs": {
                        "A": { "type": "variables_get", "fields": { "VAR": temp_var } },
                        "B": { "type": "text", "fields": { "TEXT": "" } }
                    }
                 }
            },
            "statement_inputs": {
                 "DO0": {
                    "type": "lists_setIndex",
                    "fields": { "MODE": "INSERT", "WHERE": "LAST" },
                    "value_inputs": {
                        "LIST": { "type": "variables_get", "fields": { "VAR": res_var } },
                        "TO": {
                            "type": "math_to_int",
                            "value_inputs": {
                                "VALUE": { "type": "variables_get", "fields": { "VAR": temp_var } }
                            }
                        }
                    }
                }
            }
        }

        # 6. Assign to real name
        final_assign = {
            "type": "variables_set",
            "fields": { "VAR": name },
            "value_inputs": {
                "VALUE": { "type": "variables_get", "fields": { "VAR": res_var } }
            }
        }

        # Chain main sequence
        n1["next"] = n2
        n2["next"] = n3
        n3["next"] = loop
        loop["next"] = final_check
        final_check["next"] = final_assign

        return n1

    def _compile_derived(self, drv: Dict) -> Dict:
        return {
            "type": "variables_set",
            "fields": { "VAR": drv["name"] },
            "value_inputs": { "VALUE": self._compile_expression(drv["expression"]) }
        }
    
    def _compile_if(self, condition: Dict, actions: Dict) -> Dict:
         return {
            "type": "controls_if",
            "value_inputs": { "IF0": self._compile_logic_expression(condition) if "op" in condition else self._compile_expression(condition) },
            "statement_inputs": {
                "DO0": self._compile_legacy_actions(actions.get("then", [])),
                "ELSE": self._compile_legacy_actions(actions.get("else", []))
            }
         }

    def _compile_legacy_actions(self, actions):
        head = None
        current = None
        for action in actions:
            if action["type"] == "print":
                node = { "type": "text_print", "value_inputs": { "TEXT": { "type": "text", "fields": { "TEXT": action["value"] } } } }
                head, current = self._chain(head, current, node)
        return head

    def _compile_value(self, v: Union[str, int, float]) -> Dict:
        if isinstance(v, (int, float)):
            return {
                "type": "math_number",
                "fields": {
                    "NUM": str(v)
                }
            }
        # Variable
        return {
            "type": "variables_get",
            "fields": {
                "VAR": str(v)
            }
        }
