from extract_feature import openai_extract_seeking_all


def get_seeking(post : dict ) -> str:
    return (post.get("seeking") or "").strip()

def extract_all_from_seeking(seeking : str) -> str:
    return openai_extract_seeking_all(seeking)

# def extract_task_from_seeking(seeking : str)-> str :
#     return openai_extract_task(seeking)

# def extract_trouble_from_seeking(seeking : str)-> str :
#     return openai_extract_trouble(seeking)

