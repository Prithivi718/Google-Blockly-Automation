import json
from pathlib import Path
from typing import Dict, List, Optional


class CapabilityError(Exception):
    pass


class CapabilityValidator:
    def __init__(self, normalized_blocks_path: str):
        self.blocks = self._load_blocks(normalized_blocks_path)
        self.block_types = {b["type"] for b in self.blocks}

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
    def validate(self, semantic_plan: Dict) -> Dict:
        try:
            self._validate_inputs(semantic_plan.get("inputs", []))
            
            if "program" in semantic_plan:
                self._validate_program(semantic_plan["program"])
            else:
                self._validate_derived(semantic_plan.get("derived", []))
                self._validate_condition(semantic_plan.get("condition"))
                self._validate_actions(semantic_plan.get("actions", {}))
                
        except CapabilityError as e:
            return {"status": "error", "reason": str(e)}

        return {"status": "ok"}

    # ---------------------------
    # Helpers
    # ---------------------------
    def _require(self, block_type: str):
        if block_type not in self.block_types:
            raise CapabilityError(f"missing_block: {block_type}")

    # ---------------------------
    # Validators
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
            var_name = step.get("var")
            # 1. Ban string-encoded indexed targets
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
            # self._validate_expression(step.get("list")) 
            self._validate_program(step.get("body", []))
        
        elif step_type == "loop_repeat":
            self._require("controls_for") # or equivalent
            # Check for bad bounds
            to_val = step.get("to")
            if isinstance(to_val, dict) and to_val.get("op") == "len":
                # If to is len(A), and loop is inclusive, this might be OOB if used as index.
                # Use a warning or stricter check if we know it's inclusive.
                # Assuming standard Blockly 'controls_for' is inclusive.
                # We flag it as "upper_bound_len_used_as_index" if we see access inside?
                # For now, just simplistic check:
                 pass
            self._validate_program(step.get("body", []))

        elif step_type == "while":
            self._require("controls_whileUntil")
            self._validate_condition(step.get("condition"))
            self._validate_program(step.get("body", []))

        elif step_type == "list_set":
             self._require("lists_setIndex")
             # Check index bounds logic if possible
             self._validate_expression(step.get("index"))
             self._validate_expression(step.get("value"))

        elif step_type == "list_op":
            # list_op might be redundant if list_set/list_get are distinct types now
            pass
            
        elif step_type in ["break", "continue"]:
            self._require("controls_flow_statements")

        else:
            # raise CapabilityError(f"Unknown step type: {step_type}")
            pass 

    def _validate_expression(self, expr):
        if isinstance(expr, dict):
            op = expr.get("op")
            
            # 2. List indexing bounds rule
            if op == "list_get":
                self._require("lists_getIndex")
                index = expr.get("args")[1]
                # Static check for literal 'len(A)'
                if isinstance(index, dict) and index.get("op") == "len":
                     raise CapabilityError("index_not_provably_in_bounds: len() as index")
                if self._can_prove_out_of_bounds(index):
                     raise CapabilityError("index_not_provably_in_bounds")

            if op == "create_list":
                self._require("lists_create_with")
                for arg in expr.get("args", []):
                    self._validate_expression(arg)
            
            # Recurse
            if "args" in expr:
                for arg in expr["args"]:
                    self._validate_expression(arg)
            if "left" in expr:
                self._validate_expression(expr["left"])
            if "right" in expr:
                self._validate_expression(expr["right"])
    
    def _can_prove_out_of_bounds(self, index_expr):
        # Simplistic static proof
        # If integer literal < 0, it's bad (unless python negative indexing allowed? Plan says 0-based)
        if isinstance(index_expr, int) and index_expr < 0:
            return True
        return False

    def _validate_derived(self, derived):
        pass 

    def _validate_condition(self, condition: Dict):
        if not condition:
            return
        if "left" in condition:
            self._validate_expression(condition["left"])
        if "right" in condition:
            self._validate_expression(condition["right"])
