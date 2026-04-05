import json
from pathlib import Path
from typing import Dict, List, Optional, Set


class CapabilityError(Exception):
    pass


class CapabilityValidator:
    def __init__(self, normalized_blocks_path: str):
        self.blocks = self._load_blocks(normalized_blocks_path)
        self.block_map = {b["type"]: b for b in self.blocks}
        self.block_types = set(self.block_map.keys())

    # ---------------------------
    # Load schema
    # ---------------------------
    def _load_blocks(self, path: str) -> List[Dict]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"normalized_blocks.json not found: {path}")

        data = json.loads(p.read_text(encoding='utf-8'))

        if not isinstance(data, list):
            raise TypeError("normalized_blocks.json must be a list")

        for i, block in enumerate(data):
            if "type" not in block:
                raise KeyError(f"Block at index {i} missing 'type'")

        return data

    # ---------------------------
    # Public API
    # ---------------------------
    def validate(self, plan: Dict) -> Dict:
        """
        Validates either:
          - Old Semantic IR format: { "inputs": [...], "program": [...] }
          - Raw Blockly block tree: { "type": "...", "value_inputs": {...}, ... }
        """
        try:
            if not isinstance(plan, dict):
                raise CapabilityError("root_must_be_object")

            # IR path (two-stage pipeline)
            if "inputs" in plan or "program" in plan:
                self._validate_inputs(plan.get("inputs", []))
                self._validate_program(plan.get("program", []))
            else:
                # Raw Blockly block tree (post-compilation path)
                self._validate_block(plan)

        except CapabilityError as e:
            return {"status": "error", "reason": str(e)}

        return {"status": "ok"}

    # ---------------------------
    # IR Validators
    # ---------------------------
    def _validate_inputs(self, inputs: List[Dict]):
        if not inputs:
            return

        self._require("variables_set")

        for inp in inputs:
            if "name" not in inp or "type" not in inp:
                raise CapabilityError("invalid_input_schema")

    def _validate_program(self, program: List[Dict]):
        if not isinstance(program, list):
            raise CapabilityError("program must be a list of instructions")

        for step in program:
            self._validate_step(step)

    def _validate_step(self, step: Dict):
        step_type = step.get("type")
        if not step_type:
            raise CapabilityError("Step missing 'type'")

        if step_type == "assign":
            var_name = step.get("var", "")
            # Ban string-encoded indexed targets like "A[i]"
            if "[" in var_name or "]" in var_name:
                raise CapabilityError(f"indexed_assignment_as_string: {var_name}")
            self._require("variables_set")
            self._validate_expression(step.get("value"))

        elif step_type == "print":
            self._require("text_print")
            self._validate_expression(step.get("value"))

        elif step_type == "if":
            self._require("controls_if")
            self._validate_condition(step.get("condition"))
            self._validate_program(step.get("then", []))
            self._validate_program(step.get("else", []))

        elif step_type == "foreach":
            self._require("controls_forEach")
            self._validate_expression(step.get("list"))
            self._validate_program(step.get("body", []))

        elif step_type == "loop_repeat":
            self._require("controls_for")
            # Check for bad upper bounds
            to_val = step.get("to")
            if isinstance(to_val, dict) and to_val.get("op") == "len":
                # len() as upper bound in controls_for is fine — it's inclusive in Blockly
                pass
            self._validate_program(step.get("body", []))

        elif step_type == "while":
            self._require("controls_repeat_while")
            self._validate_condition(step.get("condition"))
            self._validate_program(step.get("body", []))

        elif step_type == "list_set":
            self._require("lists_setIndex")
            self._validate_expression(step.get("index"))
            self._validate_expression(step.get("value"))

        elif step_type in ["break", "continue"]:
            self._require("controls_flow_statements")

        elif step_type == "list_op":
            operation = step.get("operation")
            if operation not in {"append"}:
                raise CapabilityError(f"unsupported_list_op: {operation}")
            self._require("lists_append")
            self._validate_expression(step.get("value"))

        elif step_type == "return":
            self._require("controls_return")
            self._validate_expression(step.get("value"))

        else:
            # Unknown step types are allowed to pass — compiler will raise if needed
            pass

    def _validate_expression(self, expr):
        if expr is None:
            return

        SUPPORTED_OPS = {
            "number", "+", "-", "*", "/", "mod",
            "abs", "min", "max",
            "to_string", "to_number",
            "text", "text_length", "text_getSubstring",
            "list_get", "create_list", "len",
            ">", "<", ">=", "<=", "==", "!=",
            "and", "or", "not"
        }

        if isinstance(expr, dict):
            op = expr.get("op")

            if op not in SUPPORTED_OPS:
                raise CapabilityError(f"unsupported_op: {op}")

            # List indexing bounds check
            if op == "list_get":
                self._require("lists_getIndex")
                args = expr.get("args", [])
                if len(args) >= 2:
                    index = args[1]
                    # Static: literal index of len(list) would be out of bounds
                    if isinstance(index, dict) and index.get("op") == "len":
                        raise CapabilityError("index_not_provably_in_bounds: len() as index")
                    if self._can_prove_out_of_bounds(index):
                        raise CapabilityError("index_not_provably_in_bounds")

            if op == "create_list":
                self._require("lists_create_with")
                for arg in expr.get("args", []):
                    self._validate_expression(arg)

            # Recurse into args / left / right
            if "args" in expr:
                for arg in expr["args"]:
                    self._validate_expression(arg)
            if "left" in expr:
                self._validate_expression(expr["left"])
            if "right" in expr:
                self._validate_expression(expr["right"])

        elif isinstance(expr, (int, float, str)):
            # Literals and variable name strings are always valid
            pass

    def _can_prove_out_of_bounds(self, index_expr) -> bool:
        """Return True if a literal index is provably out of bounds (< 0)."""
        if isinstance(index_expr, int) and index_expr < 0:
            return True
        return False

    def _validate_derived(self, derived):
        """Validate a derived variable definition (legacy IR field)."""
        pass

    def _validate_condition(self, condition: Dict):
        if not condition:
            return
        if isinstance(condition, dict):
            op = condition.get("op")
            if op:
                self._validate_expression(condition)
            if "left" in condition:
                self._validate_expression(condition["left"])
            if "right" in condition:
                self._validate_expression(condition["right"])

    def _validate_actions(self, actions: Dict):
        if not actions:
            return
        for action in actions.get("then", []):
            self._require("text_print")
        for action in actions.get("else", []):
            self._require("text_print")

    # ---------------------------
    # Raw Blockly Block Validators
    # (used for post-compilation verification)
    # ---------------------------
    def _validate_block(self, node: Dict):
        if not isinstance(node, dict):
            raise CapabilityError("invalid_block_structure")

        block_type = node.get("type")
        if not block_type:
            raise CapabilityError("missing_block_type")

        if block_type not in self.block_map:
            raise CapabilityError(f"unknown_block: {block_type}")

        schema = self.block_map[block_type]
        self._validate_fields(node, schema)
        self._validate_value_inputs(node, schema)
        self._validate_statement_inputs(node, schema)

        if node.get("next"):
            self._validate_block(node["next"])

    def _validate_fields(self, node, schema):
        schema_fields = schema.get("fields", {})
        node_fields = node.get("fields", {})

        for field_name, field_schema in schema_fields.items():
            if field_schema.get("required") and field_name not in node_fields:
                raise CapabilityError(f"missing_field: {field_name}")

            if field_name in node_fields:
                value = node_fields[field_name]
                allowed = field_schema.get("allowed") or field_schema.get("values")
                if allowed and value not in allowed:
                    raise CapabilityError(f"invalid_field_value: {field_name}={value}")

    def _validate_value_inputs(self, node, schema):
        schema_inputs = schema.get("value_inputs", {})
        node_inputs = node.get("value_inputs", {})

        for input_name in schema_inputs:
            if input_name not in node_inputs:
                raise CapabilityError(f"missing_value_input: {input_name}")
            self._validate_block(node_inputs[input_name])

    def _validate_statement_inputs(self, node, schema):
        schema_inputs = schema.get("statement_inputs", {})
        node_inputs = node.get("statement_inputs", {})

        for input_name in schema_inputs:
            if input_name not in node_inputs:
                raise CapabilityError(f"missing_statement_input: {input_name}")
            self._validate_block(node_inputs[input_name])

    # ---------------------------
    # Helpers
    # ---------------------------
    def _require(self, block_type: str):
        if block_type not in self.block_types:
            raise CapabilityError(f"missing_block: {block_type}")
