import re
from datetime import datetime


def build_queue_from_text(content: str):
    problems = []
    lines = [line.strip() for line in content.splitlines()]

    current_problem = None
    set_no = 1  # default set number
    next_line_is_statement = False

    for line in lines:
        # Skip empty lines and header lines
        if not line or line.startswith("Subject:") or line.startswith("From:") or \
           line.startswith("ASSIGNMENT ID:") or line.startswith("TEAM") or \
           line.startswith("EMAIL:") or line.startswith("=") or \
           line.startswith("Hello") or line.startswith("You have been assigned"):
            continue

        # First, try to match the new email format: "1. [statement] (PID-XXXX)"
        # This pattern matches: number, period, space, statement, space, (PID-XXXX)
        # The statement is captured until we find space(s) followed by (PID-XXXX)
        email_format_match = re.match(r"(\d+)\.\s+(.+?)\s+\(PID-(\d+)\)", line)
        if email_format_match:
            # Save previous problem if exists
            if current_problem:
                current_problem["statement"] = current_problem["statement"].strip()
                problems.append(current_problem)

            problem_no = int(email_format_match.group(1))
            statement = email_format_match.group(2).strip()
            problem_id = f"PID-{email_format_match.group(3).zfill(4)}"  # Keep original PID format

            timestamp = datetime.utcnow().isoformat()

            current_problem = {
                "problem_id": problem_id,
                "problem_no": problem_no,
                "set_no": set_no,  # Use current set_no or default to 1
                "statement": statement,
                "status": "PENDING",
                "assigned_to": None,
                "artifacts": {
                    "solution_txt": None,
                    "solution_xml": None
                },
                "timestamps": {
                    "created_at": timestamp,
                    "updated_at": timestamp
                }
            }
            # Allow continuation of statement on next lines (for multi-line statements)
            next_line_is_statement = False
            continue

        # Detect SET number (e.g. "SET 1", "SET 2") - for old format
        set_match = re.match(r"SET\s+(\d+)", line, re.IGNORECASE)
        if set_match:
            set_no = int(set_match.group(1))
            continue

        # Detect problem header (e.g. "Problem 1:", "Problem 2:") - for old format
        problem_match = re.match(r"Problem\s+(\d+):", line, re.IGNORECASE)
        if problem_match:
            # Save previous problem
            if current_problem:
                current_problem["statement"] = current_problem["statement"].strip()
                problems.append(current_problem)

            problem_no = int(problem_match.group(1))
            # Generate problem_id based on set and problem number
            problem_id = f"PID-{set_no:02d}{problem_no:02d}"

            timestamp = datetime.utcnow().isoformat()

            current_problem = {
                "problem_id": problem_id,
                "problem_no": problem_no,
                "set_no": set_no,
                "statement": "",  # Will be filled on next line
                "status": "PENDING",
                "assigned_to": None,
                "artifacts": {
                    "solution_txt": None,
                    "solution_xml": None
                },
                "timestamps": {
                    "created_at": timestamp,
                    "updated_at": timestamp
                }
            }
            next_line_is_statement = True
        elif current_problem and line:
            # This is the problem statement (line after "Problem X:" or continuation)
            if next_line_is_statement:
                current_problem["statement"] = line
                next_line_is_statement = False
            else:
                # Continuation of the problem statement (for both formats)
                # Skip if line looks like it starts a new problem
                if not re.match(r"^\d+\.\s+", line):
                    current_problem["statement"] += " " + line

    # Append last problem
    if current_problem:
        current_problem["statement"] = current_problem["statement"].strip()
        problems.append(current_problem)

    return problems




