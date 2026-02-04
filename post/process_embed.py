from psycopg.rows import dict_row
from pathlib import Path
import sys
from get_extract import *
from embed import embed
from extract_feature import openai_extract_seeking_all
from put_db import upsert_post_vector

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))                 # db import용

from db import conn
post_id= 100068

def process_post(post: dict) -> tuple[str, str, str]:

    # post에서 seeking 접근
    seeking = (post.get("seeking") or "").strip()
    # seeking에서 task, trouble 추출
    result = openai_extract_seeking_all(seeking)
    task = result["task_items"]                      # '"A","B"'
    trouble = result["trouble_items"]                # '"X"'
    prefer = result["prefer_domain_exp"]       # True/False

    print(task)
    print(trouble)
    print(prefer)
    return task, trouble, prefer


def fetch_one_post(conn, post_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT pinfo_id, post_id, about_us, seeking FROM post_info WHERE post_id = %s",
            (post_id,)
        )
        return cur.fetchone()


# post = fetch_one_post(conn, post_id)
# c_task, c_trouble, c_prefer = process_post(post)



# # task와 trouble 임베딩
# task_text = "\n".join(c_task)          # list[str] -> str
# trouble_text = "\n".join(c_trouble)

# task_emb = embed(task_text) if task_text.strip() else None
# trouble_emb = embed(trouble_text) if trouble_text.strip() else None

# print("task_emb type/len:", type(task_emb), None if task_emb is None else len(task_emb))
# print("trouble_emb type/len:", type(trouble_emb), None if trouble_emb is None else len(trouble_emb))
# print("prefer:", c_prefer)

# upsert_post_vector(conn, post_id, task_emb, trouble_emb, c_prefer)
# print("task 벡터 INSERT 완료! ")
# print("trouble 벡터 INSERT 완료! ")

# conn.commit()