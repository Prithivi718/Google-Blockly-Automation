import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from semantic.planner import generate_semantic_plan

def test_star_pattern():
    print("Testing Star Pattern (Dynamic Mode)...")
    problem = "Print a right-angled triangle star pattern with 5 rows."
    
    plan, expansion = generate_semantic_plan(problem)
    
    print("\n--- EXPANSION ---")
    print(expansion)
    print("\n--- SEMANTIC PLAN (JSON) ---")
    print(plan)
    
    if "error" in plan:
        print(f"FAILED: {plan.get('reason')}")
    else:
        print("SUCCESS: Plan generated.")

if __name__ == "__main__":
    test_star_pattern()
