import json
import os
from pathlib import Path

def generate_block_summary(blocks_path: str) -> str:
    """
    Summarizes normalized_blocks.json into a concise Markdown for LLM grounding.
    """
    if not os.path.exists(blocks_path):
        return "Error: normalized_blocks.json not found."

    with open(blocks_path, "r", encoding="utf-8") as f:
        blocks = json.load(f)

    # Group by category for better LLM readability
    categories = {}
    for block in blocks:
        cat = block.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(block)

    summary = ["# Blockly Capability Summary\n"]
    summary.append("Use these block types EXACTLY as defined below.Each block must be used with the correct fields and inputs.Do NOT invent new structures.\n")

    for cat, cat_blocks in categories.items():
        summary.append(f"## {cat.capitalize()} Primitives")
        for b in cat_blocks:
            b_type = b.get("type")
            b_kind = b.get("kind", "statement/expression")
            
            # Extract fields (enums, etc)
            fields = []
            if b.get("fields"):
                for f_name, f_data in b["fields"].items():
                    if f_data.get("allowed"):
                        fields.append(f"{f_name}:[{'|'.join(f_data['allowed'])}]")
                    else:
                        fields.append(f"{f_name}")

            # Extract inputs
            inputs = list(b.get("value_inputs", {}).keys()) + list(b.get("statement_inputs", {}).keys())
            
            line = f"- **{b_type}** ({b_kind})"
            if fields:
                line += f" Fields: `{','.join(fields)}`"
            if inputs:
                line += f" Inputs: `{','.join(inputs)}`"
            
            summary.append(line)
        summary.append("") # Spacer

    return "\n".join(summary)

if __name__ == "__main__":
    # Test generation
    ROOT = Path(__file__).parent.parent
    BLOCKS_PATH = ROOT / "data" / "normalized_blocks.json"
    print(generate_block_summary(str(BLOCKS_PATH)))
