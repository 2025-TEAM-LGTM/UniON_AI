from extract_feature import openai_extract_task, openai_extract_task_and_trouble
from typing import List

def get_t_text(portfolio: dict) -> str:
    return (portfolio.get("t_text") or "").strip()

def get_a_text(portfolio: dict) -> str:
    return (portfolio.get("a_text") or "").strip()

def extract_task_from_t_text(t_text: str) -> str:
    return openai_extract_task(t_text)["task"]

def extract_task_from_a_text(a_text: str) -> str:
    return openai_extract_task_and_trouble(a_text)["task"]

def extract_trouble_from_a_text(a_text: str) -> str:
    return openai_extract_task_and_trouble(a_text)["trouble"]

from typing import List

def merge_tasks(task_from_t: List[str] | None, task_from_a: List[str] | None) -> List[str]:
    task_from_t = task_from_t or []
    task_from_a = task_from_a or []

    seen = set()
    merged = []
    for s in task_from_t + task_from_a:
        if isinstance(s, str):
            s = s.strip()
            if s and s not in seen:
                seen.add(s)
                merged.append(s)
    return merged

