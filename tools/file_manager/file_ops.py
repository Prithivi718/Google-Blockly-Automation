import os
import re
import json


def write_problems_file(subject, sender, body):
    clean_body = body.replace('\r\n', '\n').replace('\r', '\n')
    clean_body = re.sub(r'\n{3,}', '\n\n', clean_body).strip()

    content = (
        f"Subject: {subject}\n"
        f"From: {sender}\n\n"
        f"{clean_body}\n"
    )

    with open("problems.txt", "w", encoding="utf-8") as f:
        f.write(content)

    print("Problems saved cleanly to problems.txt")


def write_queue_json(problems, filename="queue.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(problems, file, indent=2)

    print(f"Queue initialized with {len(problems)} problems.")


def read_problems_file(filename: str) -> str:
    with open(filename, "r", encoding="utf-8") as file:
        return file.read()


def load_problem_files():
    return [
        "problems/bug.txt",
        "problems/filter_list.py",
        "problems/workspace.xml",
    ]


def get_filename(path: str) -> str:
    return os.path.basename(path)
