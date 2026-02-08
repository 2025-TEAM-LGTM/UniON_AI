from extract_feature import openai_extract_seeking_all
from typing import Dict, Any

def get_seeking(post : dict ) -> str:
    return (post.get("seeking") or "").strip()

def extract_all_from_seeking(seeking : str) -> str:
    return openai_extract_seeking_all(seeking)

def get_personality(post: Dict[str, Any]) -> Dict[str, Any]:
    return post.get("personality") or {}


# def extract_task_from_seeking(seeking : str)-> str :
#     return openai_extract_task(seeking)

# def extract_trouble_from_seeking(seeking : str)-> str :
#     return openai_extract_trouble(seeking)

