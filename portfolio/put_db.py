import psycopg

from typing import Sequence


def upsert_task_vector(
    conn,
    portfolio_id: int,
    emb: Sequence[float] | None
):
    """
    portfolio_task 테이블에 task vector upsert
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO portfolio_vector (
                portfolio_id,
                ptf_task_vector,
                updated_at
            )
            VALUES (%s, %s, now())
            ON CONFLICT (portfolio_id)
            DO UPDATE SET
                ptf_task_vector = EXCLUDED.ptf_task_vector,
                updated_at = now();
            """,
            (portfolio_id, emb if emb else None),
        )
    print("task 벡터 INSERT 완료! ")


def upsert_trouble_vector(
    conn,
    portfolio_id: int,
    emb: Sequence[float] | None
):

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO portfolio_vector (
                portfolio_id,
                ptf_trouble_vector,
                updated_at
            )
            VALUES (%s, %s, now())
            ON CONFLICT (portfolio_id)
            DO UPDATE SET
                ptf_trouble_vector = EXCLUDED.ptf_trouble_vector,
                updated_at = now();
            """,
            (portfolio_id, emb if emb else None),
        )
    print("trouble 벡터 INSERT 완료! ")
