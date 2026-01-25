"""
Semantic Planner Output Schema (Module 1)

This schema defines the ONLY structure the LLM
is allowed to output.
"""

# ------------------------------
# Input Variable Schema
# ------------------------------
INPUT_SCHEMA = {
    "name": str,        # variable name
    "type": str         # int | float | string | bool
}

# ------------------------------
# Derived Variable Schema
# ------------------------------
DERIVED_SCHEMA = {
    "name": str,
    "expression": {
        "op": str,      # semantic op (see SEMANTIC_OPS)
        "args": list    # 1 or more arguments
    }
}

# ------------------------------
# Allowed semantic operators
# ------------------------------
SEMANTIC_OPS = {
    # arithmetic
    "+", "-", "*", "/", "mod",

    # unary math
    "abs", "neg", "sqrt",

    # comparisons handled elsewhere
    # string / list
    "len", "to_string", "to_number",

    # min / max
    "min", "max"
}

# ------------------------------
# Atomic Condition Schema
# ------------------------------
CONDITION_ATOM_SCHEMA = {
    "left": object,     # var name or number
    "op": str,          # >= | <= | > | < | == | !=
    "right": object     # var name or number
}

# ------------------------------
# Condition Group Schema
# ------------------------------
CONDITION_SCHEMA = {
    "op": str,              # and | or
    "conditions": list      # list of CONDITION_ATOM_SCHEMA
}

# ------------------------------
# Action Schema
# ------------------------------
ACTION_SCHEMA = {
    "type": str,        # only "print"
    "value": str        # string literal
}

# ------------------------------
# Semantic Plan (FINAL)
# ------------------------------
SEMANTIC_PLAN_SCHEMA = {
    "inputs": list,         # list of INPUT_SCHEMA
    "derived": list,        # list of DERIVED_SCHEMA
    "condition": object,    # CONDITION_SCHEMA or null
    "actions": {
        "then": list,       # list of ACTION_SCHEMA
        "else": list        # list of ACTION_SCHEMA
    }
}

# ------------------------------
# Skeleton Library (Module 1.5)
# ------------------------------
SKELETONS = {
    "FOREACH_AGGREGATE": {
        "inputs": [{"name": "A", "type": "list<int>"}],
        "program": [
            {
                "type": "assign",
                "var": "__ACC__",
                "value": {"op": "list_get", "args": ["A", 0]}
            },
            {
                "type": "foreach",
                "var": "__ITEM__",
                "list": "A",
                "body": [
                    {
                        "type": "if",
                        "condition": {
                            "left": "__ITEM__",
                            "op": "__CMP__",
                            "right": "__ACC__"
                        },
                        "then": [
                            {
                                "type": "assign",
                                "var": "__ACC__",
                                "value": "__ITEM__"
                            }
                        ],
                        "else": []
                    }
                ]
            },
            {
                "type": "print",
                "value": "__ACC__"
            }
        ]
    },
    "INDEX_ROTATION": {
        "inputs": [{"name": "A", "type": "list<int>"}],
        "program": [
             {
                "type": "assign",
                "var": "__N__",
                "value": {"op": "len", "args": ["A"]}
             },
             {
                "type": "assign",
                "var": "__TEMP__",
                "value": {"op": "list_get", "args": ["A", "__TEMP_IDX__" ]}
             },
             {
                 "type": "loop_repeat",
                 "var": "__I__",
                 "start": 1,
                 "to": "__LIMIT__", 
                 "body": [
                     {
                         "type": "list_set",
                         "list": "A",
                         "index": "__IDX_EXPR__", 
                         "value": {"op": "list_get", "args": ["A", "__IDX_VAL__"]}
                     }
                 ]
             },
             {
                 "type": "list_set",
                 "list": "A",
                 "index": "__FINAL_IDX__",
                 "value": "__TEMP__"
             },
             {
                 "type": "print",
                 "value": "A"
             }
        ]
    },
    "MOVE_ZEROS": {
        "inputs": [{"name": "A", "type": "list<int>"}],
        "program": [
            {
                "type": "assign",
                "var": "__COUNT__",
                "value": 0
            },
            {
                "type": "foreach",
                "var": "__ITEM__",
                "list": "A",
                "body": [
                    {
                        "type": "if",
                        "condition": {
                            "left": "__ITEM__",
                            "op": "!=",
                            "right": 0
                        },
                        "then": [
                            {
                                "type": "list_set",
                                "list": "A",
                                "index": "__COUNT__",
                                "value": "__ITEM__"
                            },
                             {
                                "type": "assign",
                                "var": "__COUNT__",
                                "value": {
                                    "left": "__COUNT__",
                                    "op": "+",
                                    "right": 1
                                }
                            }
                        ],
                        "else": []
                    }
                ]
            },
             {
                 "type": "loop_repeat",
                 "var": "__I__",
                 "start": "__COUNT__",
                 "to": {"op": "len", "args": ["A"]},
                 "body": [
                     {
                         "type": "list_set",
                         "list": "A",
                         "index": "__I__",
                         "value": 0
                     }
                 ]
             },
             {
                 "type": "print",
                 "value": "A"
             }
        ]
    },
    "LINEAR_SEARCH": {
        "inputs": [
            {"name": "A", "type": "list<int>"},
            {"name": "TARGET", "type": "int"}
        ],
        "program": [
            {
                "type": "assign",
                "var": "__INDEX__",
                "value": -1
            },
            {
                "type": "assign",
                "var": "__I__",
                "value": 0
            },
            {
                "type": "foreach",
                "var": "__ITEM__",
                "list": "A",
                "body": [
                    {
                        "type": "if",
                        "condition": {
                            "left": "__ITEM__",
                            "op": "==",
                            "right": "TARGET"
                        },
                        "then": [
                            {
                                "type": "assign",
                                "var": "__INDEX__",
                                "value": "__I__"
                            },
                            {
                                "type": "break"
                            }
                        ],
                        "else": []
                    },
                    {
                        "type": "assign",
                        "var": "__I__",
                        "value": {
                            "left": "__I__",
                            "op": "+",
                            "right": 1
                        }
                    }
                ]
            },
            {
                "type": "print",
                "value": "__INDEX__"
            }
        ]
    }
}
