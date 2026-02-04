import psycopg
from typing import Sequence


def upsert_task_vector(
    conn,
    post_id: int,
    emb: Sequence[float] | None
):
    """
    post_vector 테이블에 task vector upsert
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_vector (
                post_id,
                pst_task_vector,
                updated_at
            )
            VALUES (%s, %s, now())
            ON CONFLICT (post_id)
            DO UPDATE SET
                pst_task_vector = EXCLUDED.pst_task_vector,
                updated_at = now();
            """,
            (post_id, emb if emb else None),
        )


def upsert_trouble_vector(
    conn,
    post_id: int,
    emb: Sequence[float] | None
):

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_vector (
                post_id,
                pst_trouble_vector,
                updated_at
            )
            VALUES (%s, %s, now())
            ON CONFLICT (post_id)
            DO UPDATE SET
                pst_trouble_vector = EXCLUDED.pst_trouble_vector,
                updated_at = now();
            """,
            (post_id, emb if emb else None),
        )

def upsert_post_vector(
    conn,
    post_id: int,
    task_emb: Sequence[float] | None,      # task 벡터
    trouble_emb: Sequence[float] | None,   # trouble 벡터
    prefer: bool                           # domain 경험 우대 언급 여부
):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_vector (
                post_id,
                pst_task_vector,
                pst_trouble_vector,
                pst_domain_exp,
                updated_at
            )
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (post_id)
            DO UPDATE SET
                pst_task_vector = EXCLUDED.pst_task_vector,
                pst_trouble_vector = EXCLUDED.pst_trouble_vector,
                pst_domain_exp = EXCLUDED.pst_domain_exp,
                updated_at = now();
            """,
            (
                post_id,
                task_emb if task_emb else None,
                trouble_emb if trouble_emb else None,
                bool(prefer),
            ),
        )

    print(f"{post_id} post 벡터 INSERT 완료!")
