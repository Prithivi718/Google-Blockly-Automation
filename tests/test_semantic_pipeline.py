import unittest
import sys
import os
import json
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from semantic.planner import generate_semantic_plan
from semantic.validator import CapabilityValidator, CapabilityError
from semantic.compiler import SemanticCompiler

# Mock Normalized Blocks Path (using real one)
BLOCKS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "normalized_blocks.json"))

class TestSemanticPipeline(unittest.TestCase):
    
    @patch("semantic.planner.OpenAI")
    @patch("semantic.question_expander.OpenAI")
    def test_pipeline_positive(self, mock_openai_expander, mock_openai_planner):
        """
        Test the full pipeline for 'Largest Element'.
        Expects FOREACH_AGGREGATE skeleton to be used.
        """
        problem = "Find the largest element in an array A"
        
        # 1. Setup Mocks
        # Mock Expander Response
        mock_expander_instance = MagicMock()
        mock_openai_expander.return_value = mock_expander_instance
        mock_expander_instance.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="Find the largest element in input list A.\n# PROBLEM_TAG: largest_element"))
        ]

        # Mock Planner Filler Response (The filled skeleton)
        filled_skeleton = {
            "inputs": [{"name": "A", "type": "list<int>"}],
            "program": [
                {
                    "type": "assign",
                    "var": "max_val",
                    "value": {"op": "list_get", "args": ["A", 0]}
                },
                {
                    "type": "foreach",
                    "var": "item",
                    "list": "A",
                    "body": [
                        {
                            "type": "if",
                            "condition": {
                                "left": "item",
                                "op": ">",
                                "right": "max_val"
                            },
                            "then": [
                                {
                                    "type": "assign",
                                    "var": "max_val",
                                    "value": "item"
                                }
                            ],
                            "else": []
                        }
                    ]
                },
                {
                    "type": "print",
                    "value": "max_val"
                }
            ]
        }
        mock_planner_instance = MagicMock()
        mock_openai_planner.return_value = mock_planner_instance
        mock_planner_instance.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=json.dumps(filled_skeleton)))
        ]

        # 2. Planner Execution
        try:
            plan, _ = generate_semantic_plan(problem)
        except Exception as e:
            self.fail(f"Planner failed: {e}")

        self.assertIn("program", plan)
        self.assertEqual(plan["program"][0]["type"], "assign")
        
        # 3. Validator
        validator = CapabilityValidator(BLOCKS_PATH)
        res = validator.validate(plan)
        self.assertEqual(res["status"], "ok", f"Validation failed: {res}")

        # 4. Compiler
        compiler = SemanticCompiler(validator)
        try:
            blockly_xml = compiler.compile(plan)
        except Exception as e:
            self.fail(f"Compiler failed: {e}")
            
        self.assertIsNotNone(blockly_xml)


    def test_validator_negative_len_index(self):
        """
        Test that validator rejects 'len(A)' used as an index.
        """
        bad_plan = {
            "inputs": [{"name": "A", "type": "list<int>"}],
            "program": [
                {
                    "type": "assign",
                    "var": "x",
                    "value": {
                        "op": "list_get",
                        "args": ["A", {"op": "len", "args": ["A"]}] 
                    }
                }
            ]
        }
        
        validator = CapabilityValidator(BLOCKS_PATH)
        res = validator.validate(bad_plan)
        self.assertEqual(res["status"], "error")
        if "index_not_provably_in_bounds" not in res["reason"]:
             print(f"Warning: Expected failure reason to contain 'index_not_provably_in_bounds', got '{res['reason']}'")


    def test_validator_negative_string_assign(self):
        """
        Test that validator rejects string-encoded assignment like 'A[i]'.
        """
        bad_plan = {
            "inputs": [{"name": "A", "type": "list<int>"}],
            "program": [
                {
                    "type": "assign",
                    "var": "A[0]", # ERROR
                    "value": 1
                }
            ]
        }
        
        validator = CapabilityValidator(BLOCKS_PATH)
        with self.assertRaises(CapabilityError) as cm:
            validator._validate_step(bad_plan["program"][0])
        self.assertIn("indexed_assignment_as_string", str(cm.exception))


    def test_validator_negative_oob_literal(self):
        """
        Test that validator rejects static OOB literal (if we implemented check, 
        currently simple check for < 0).
        """
        bad_plan = {
            "inputs": [{"name": "A", "type": "list<int>"}],
            "program": [
                {
                    "type": "assign",
                    "var": "x",
                    "value": {
                        "op": "list_get",
                        "args": ["A", -1] 
                    }
                }
            ]
        }
        validator = CapabilityValidator(BLOCKS_PATH)
        with self.assertRaises(CapabilityError) as cm:
           validator._validate_expression(bad_plan["program"][0]["value"])
        self.assertIn("index_not_provably_in_bounds", str(cm.exception))

if __name__ == "__main__":
    unittest.main()
