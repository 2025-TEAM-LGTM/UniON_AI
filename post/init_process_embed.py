from psycopg.rows import dict_row
from pathlib import Path
import sys
BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))                 # db import용

from db import conn
from process_embed import process_post
from embed import embed
from put_db import upsert_post_vector


def fetch_posts(
    conn,
    *,
    limit: int = 200,
    only_missing: bool = True,
    start_post_id: int | None = None,
) -> list[dict]:
    """
    post들을 post_id 오름차순으로 가져오되,
    필요하면 start_post_id 이상부터만 가져온다.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        params: list = []

        base_sql = """
            SELECT p.post_id, pi.seeking
            FROM post p
            JOIN post_info pi ON pi.post_id = p.post_id
        """

        if only_missing:
            base_sql += """
            LEFT JOIN post_vector pv ON pv.post_id = p.post_id
            WHERE pi.seeking IS NOT NULL
              AND (pv.post_id IS NULL
                   OR pv.pst_task_vector IS NULL
                   OR pv.pst_trouble_vector IS NULL)
            """
        else:
            base_sql += """
            WHERE pi.seeking IS NOT NULL
            """

        if start_post_id is not None:
            base_sql += " AND p.post_id >= %s"
            params.append(start_post_id)

        base_sql += """
            ORDER BY p.post_id
            LIMIT %s
        """
        params.append(limit)

        cur.execute(base_sql, params)
        return cur.fetchall()


def init_post_vectors(
    conn,
    *,
    limit: int = 200,
    commit_every: int = 20,
    only_missing: bool = True,
    start_post_id: int | None = None,
):
    posts = fetch_posts(
        conn,
        limit=limit,
        only_missing=only_missing,
        start_post_id=start_post_id,
    )
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


# 예시: post_id 100001번부터 25개만 처리
init_post_vectors(conn, limit=25, commit_every=5, only_missing=True, start_post_id=100001)
