from pathlib import Path


def write_fallback_outputs(
    problem_id: str,
    xml: str,
    python_code: str,
    output_dir: Path
):
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_path = output_dir / f"TEAM_ID0602_Mem2_{problem_id}.xml"
    py_path = output_dir / f"TEAM_ID0602_Mem2_{problem_id}.txt"

    xml_path.write_text(xml, encoding='utf-8')
    py_path.write_text(python_code, encoding='utf-8')

    return {
        "xml_path": str(xml_path),
        "python_path": str(py_path),
        "status": "fallback"
    }
