from extract_feature import openai_extract_task, openai_extract_task_and_trouble

def get_t_text(portfolio: dict) -> str:
    return (portfolio.get("t_text") or "").strip()

def get_a_text(portfolio: dict) -> str:
    return (portfolio.get("a_text") or "").strip()

def extract_task_from_t_text(t_text: str) -> str:
    return openai_extract_task(t_text)

def extract_task_from_a_text(a_text: str) -> str:
    return openai_extract_task_and_trouble(a_text)["task"]

def extract_trouble_from_a_text(a_text: str) -> str:
    return openai_extract_task_and_trouble(a_text)["trouble"]

def merge_tasks(task_from_t: str, task_from_a: str) -> str:
    # 간단 병합: 둘 다 있으면 줄바꿈으로 이어붙이기
    task_from_t = (task_from_t or "").strip()
    task_from_a = (task_from_a or "").strip()
    if task_from_t and task_from_a:
        return task_from_t + "\n" + task_from_a
    return task_from_t or task_from_a
