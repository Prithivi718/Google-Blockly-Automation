# run_test.py
import json
from pathlib import Path
import subprocess
from semantic.validator import CapabilityValidator
from semantic.compiler import SemanticCompiler
from semantic.planner import generate_semantic_plan

ROOT = Path(__file__).parent
NORMALIZED_BLOCKS = ROOT / "data" / "normalized_blocks.json"
BLOCK_TREE_OUT = ROOT / "semantic" / "output" / "block_tree.json"

problem_text = "Check whether three sides can form a valid triangle."

# Handcrafted semantic plan equivalent to the sample problem:
semantic_plan = generate_semantic_plan(problem_text)
print(semantic_plan)


# 1) Validate
validator = CapabilityValidator(str(NORMALIZED_BLOCKS))
v = validator.validate(semantic_plan)
print("Validator:", v)
if v["status"] != "ok":
    raise SystemExit("Capability validation failed")

# 2) Compile
compiler = SemanticCompiler()
block_tree = compiler.compile(semantic_plan)
BLOCK_TREE_OUT.parent.mkdir(parents=True, exist_ok=True)
BLOCK_TREE_OUT.write_text(json.dumps(block_tree, indent=2), encoding='utf-8')
print("Wrote block_tree.json")

# 3) Node XML generation
subprocess.run(["node", "generate_xml.js"], cwd=ROOT / "assembler", check=True)
print("XML generated")

# 4) Runner (Playwright) execution
subprocess.run(["node", "runner_execute.js"], cwd=ROOT / "runner", check=True)
print("Runner completed")
