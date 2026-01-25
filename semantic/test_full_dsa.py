from semantic.validator import CapabilityValidator
from semantic.compiler import SemanticCompiler
import json
from pathlib import Path

def test_full_dsa_workflow():
    print("🧪 Testing Full DSA Workflow (Validator -> Compiler)")
    
    # Simulate a Semantic Plan for "Sum of List"
    # Logic:
    # 1. Input list
    # 2. total = 0
    # 3. foreach item in list: total = total + item
    # 4. print total
    
    semantic_plan = {
        "inputs": [
            { "name": "my_list", "type": "list<int>" }
        ],
        "program": [
            {
                "type": "assign",
                "var": "total",
                "value": { "op": "number", "value": 0 }
            },
            {
                "type": "foreach",
                "var": "item",
                "list": "my_list", # In real blockly this might need to be a var_get block
                "body": [
                    {
                        "type": "assign",
                        "var": "total",
                        "value": { 
                            "op": "+",
                            "args": ["total", "item"]
                        }
                    }
                ]
            },
            {
                "type": "print",
                "value": "total"
            }
        ]
    }
    
    print("📄 Semantic Plan:")
    print(json.dumps(semantic_plan, indent=2))
    
    # 1. Validator
    print("\n🔍 Validating...")
    validator = CapabilityValidator(str(Path("data/normalized_blocks.json").absolute()))
    validation = validator.validate(semantic_plan)
    print(f"Validation Result: {validation}")
    
    if validation["status"] != "ok":
        print("❌ Validation Failed!")
        return
        
    # 2. Compiler
    print("\n⚙️ Compiling...")
    compiler = SemanticCompiler()
    try:
        block_tree = compiler.compile(semantic_plan)
        print("✅ Compilation Successful!")
        print(json.dumps(block_tree, indent=2))
    except Exception as e:
        print(f"❌ Compilation Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    # Redirect stdout to a file
    with open("test_dsa_output.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        test_full_dsa_workflow()

