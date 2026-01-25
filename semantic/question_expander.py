import os
from dotenv import load_dotenv
from openai import OpenAI

from semantic.question_expander_prompt import system_prompt, user_prompt

load_dotenv()


class QuestionExpansionError(Exception):
    pass


def expand_problem(problem_text: str) -> str:
    if not problem_text or not isinstance(problem_text, str):
        raise QuestionExpansionError("Problem text must be a non-empty string")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise QuestionExpansionError("OPENROUTER_API_KEY not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            # model="qwen/qwen-2.5-7b-instruct",
            # model="deepseek/deepseek-r1-0528:free",
            model="openai/gpt-4o-mini",
            # model="google/gemini-2.0-flash-exp:free",
            messages=[
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_prompt(problem_text)}
            ],
            temperature=0
        )
    except Exception as e:
        raise QuestionExpansionError(f"LLM call failed: {e}")

    expanded = response.choices[0].message.content.strip()

    if not expanded.strip():
        print("Expanded problem is empty")
        return problem_text

    try:
        print(f"\nExpanded Question:\n{expanded}")
    except UnicodeEncodeError:
        print(f"\nExpanded Question:\n{expanded.encode('ascii', errors='replace').decode('ascii')}")

    return expanded
