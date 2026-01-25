import unittest
import sys
import os
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import process_problem

# Paths
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
ASSEMBLER_OUT = ROOT / "assembler" / "output"
RUNNER_OUT = ROOT / "runner" / "output"
OUTPUTS = ROOT / "outputs"

class TestMainIntegration(unittest.TestCase):
    
    def setUp(self):
        # Clean up previous outputs
        if ASSEMBLER_OUT.exists():
            shutil.rmtree(ASSEMBLER_OUT)
        if RUNNER_OUT.exists():
            shutil.rmtree(RUNNER_OUT)
        if OUTPUTS.exists():
            shutil.rmtree(OUTPUTS)
            
        ASSEMBLER_OUT.mkdir(parents=True, exist_ok=True)
        RUNNER_OUT.mkdir(parents=True, exist_ok=True)
        OUTPUTS.mkdir(parents=True, exist_ok=True)

    @patch("main.generate_semantic_plan")
    @patch("main.run") # Patching the helper 'run' which calls subprocess
    def test_process_problem_success(self, mock_run, mock_planner):
        # 1. Mock Planner Return
        mock_planner.return_value = {
            "inputs": [{"name": "A", "type": "list<int>"}],
            "program": [
                {
                    "type": "assign",
                    "var": "max_val", 
                    "value": {"op": "list_get", "args": ["A", 0]}
                },
                {
                    "type": "print",
                    "value": "max_val"
                }
            ]
        }

        # 2. Mock Subprocess Execution (Side Effects)
        def side_effect_run(cmd, cwd):
            # Check cwd to decide what to generate
            cwd_str = str(cwd)
            if "assembler" in cwd_str:
                # Simulate generating XML
                (ASSEMBLER_OUT / "program.xml").write_text("<xml>Mocked XML</xml>", encoding="utf-8")
            elif "runner" in cwd_str:
                # Simulate generating Python
                # User wanted "Human in loop" code - we simulate the output here.
                # In strict flow, this comes from runner_execute.js -> Blockly
                python_code = "max_val = A[0]\nprint(max_val)"
                (RUNNER_OUT / "result.txt").write_text(python_code, encoding="utf-8")
        
        mock_run.side_effect = side_effect_run

        # 3. Define Problem
        problem_id = "PID-1001"
        team_id = "TEST_TEAM"
        problem = {
            "problem_id": problem_id,
            "description": "Find largest element"
        }

        # 4. Run Process
        try:
            process_problem(problem, team_id)
        except Exception as e:
            self.fail(f"process_problem failed: {e}")

        # 5. Verify Outputs
        problem_dir = OUTPUTS / f"Problem_{problem_id}"
        self.assertTrue(problem_dir.exists(), "Problem output folder not created")
        
        py_file = problem_dir / f"{team_id}_TL_{problem_id}.txt"
        xml_file = problem_dir / f"{team_id}_TL_{problem_id}.xml"
        
        self.assertTrue(py_file.exists(), "Python file not copied")
        self.assertTrue(xml_file.exists(), "XML file not copied")
        
        self.assertEqual(py_file.read_text(encoding='utf-8'), "max_val = A[0]\nprint(max_val)")
        self.assertEqual(xml_file.read_text(encoding='utf-8'), "<xml>Mocked XML</xml>")
        
        print("\nIntegration test passed: Output files verified.")

if __name__ == "__main__":
    unittest.main()
