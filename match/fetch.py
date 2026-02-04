# 입력받은 post_id에 대해, recruit하고 있는 role이 동일한 portfolio만 fetch
from db import conn
from psycopg.rows import dict_row


def fetch_candidate_portfolios(conn, post_id: int) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT ptf.portfolio_id
            FROM portfolio ptf
            JOIN post_recruit_role prr
              ON ptf.role_id = prr.role_id
            WHERE prr.post_id = %s
            """,
            (post_id,)
        )
        return [row[0] for row in cur.fetchall()]
