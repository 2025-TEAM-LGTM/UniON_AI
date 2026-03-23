from psycopg.rows import dict_row
from pathlib import Path
import sys

from .get_extract import *
from .embed import embed
from .extract_feature import openai_extract_seeking_all
from .put_db import upsert_post_vector

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(BASE_DIR))

from db import conn

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

def put_post_vector(post_id: int):

    post = fetch_one_post(conn, post_id)
    if post is None:
        raise ValueError(f"post not found. post_id={post_id}")
    else:
        print("fetched post:", post)
    c_task, c_trouble, c_prefer = process_post(post)

    # task와 trouble 임베딩
    task_text = "\n".join(c_task)          # list[str] -> str
    trouble_text = "\n".join(c_trouble)

    task_emb = embed(task_text) if task_text.strip() else None
    trouble_emb = embed(trouble_text) if trouble_text.strip() else None

    upsert_post_vector(conn, post_id, task_emb, trouble_emb, c_prefer)

    conn.commit()