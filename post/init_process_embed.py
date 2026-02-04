from psycopg.rows import dict_row
from pathlib import Path
import sys
BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))                 # db import용

from db import conn
from process_embed import process_post
from embed import embed
from put_db import upsert_post_vector

def fetch_posts(conn, limit: int = 200, only_missing: bool = True) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        if only_missing:
            cur.execute(
                """
                SELECT p.post_id, pi.seeking
                FROM post p
                JOIN post_info pi ON pi.post_id = p.post_id
                LEFT JOIN post_vector pv ON pv.post_id = p.post_id
                WHERE pi.seeking IS NOT NULL
                  AND (pv.post_id IS NULL
                       OR pv.pst_task_vector IS NULL
                       OR pv.pst_trouble_vector IS NULL)
                ORDER BY p.post_id
                LIMIT %s
                """,
                (limit,)
            )
        else:
            cur.execute(
                """
                SELECT p.post_id, pi.seeking
                FROM post p
                JOIN post_info pi ON pi.post_id = p.post_id
                WHERE pi.seeking IS NOT NULL
                ORDER BY p.post_id
                LIMIT %s
                """,
                (limit,)
            )
        return cur.fetchall()


def init_post_vectors(conn, limit: int = 200, commit_every: int = 20, only_missing: bool = True):
    posts = fetch_posts(conn, limit=limit, only_missing=only_missing)
    print(f"target={len(posts)}")

    done = 0
    for post in posts:
        post_id = int(post["post_id"])

        task_text, trouble_text, prefer = process_post(post)

        task_text = "\n".join(task_text)          # list[str] -> str
        trouble_text = "\n".join(trouble_text)

        task_emb = embed(task_text) if task_text.strip() else None
        trouble_emb = embed(trouble_text) if trouble_text.strip() else None

        prefer_bool = bool(prefer)  # prefer가 bool이면 그대로 OK

        upsert_post_vector(conn, post_id, task_emb, trouble_emb, prefer_bool)

        done += 1
        if done % commit_every == 0:
            conn.commit()
            print(f"committed {done}")

    conn.commit()
    print(f"done {done}")

init_post_vectors(conn, limit=10, commit_every=5, only_missing=True)
