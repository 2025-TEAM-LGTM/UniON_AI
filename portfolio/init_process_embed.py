from psycopg.rows import dict_row
from pathlib import Path
import sys
BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))  
               
from db import conn
from process_embed import process_portfolio
from embed import embed
from put_db import upsert_task_vector, upsert_trouble_vector


def fetch_portfolios(
    conn,
    *,
    limit: int = 200,
    only_missing: bool = True,
    start_portfolio_id: int | None = None,
) -> list[dict]:
    """
    portfolio 여러 개 가져오기
    - only_missing=True: portfolio_vector에 아직 없거나 벡터가 NULL인 것만 가져옴
    """
    with conn.cursor(row_factory=dict_row) as cur:
        params: list = []

        if only_missing:
            sql = """
                SELECT p.portfolio_id, p.t_text, p.a_text
                FROM portfolio p
                LEFT JOIN portfolio_vector pv ON pv.portfolio_id = p.portfolio_id
                WHERE (pv.portfolio_id IS NULL
                       OR pv.ptf_task_vector IS NULL
                       OR pv.ptf_trouble_vector IS NULL)
            """
        else:
            sql = """
                SELECT portfolio_id, t_text, a_text
                FROM portfolio
            """

        if start_portfolio_id is not None:
            sql += " AND p.portfolio_id >= %s" if only_missing else " WHERE portfolio_id >= %s"
            params.append(start_portfolio_id)

        sql += """
            ORDER BY p.portfolio_id
            LIMIT %s
        """
        params.append(limit)

        cur.execute(sql, params)
        return cur.fetchall()


def init_portfolio_vectors(
    conn,
    *,
    limit: int = 200,
    commit_every: int = 20,
    only_missing: bool = True,
    start_portfolio_id: int | None = None,
):
    portfolios = fetch_portfolios(
        conn,
        limit=limit,
        only_missing=only_missing,
        start_portfolio_id=start_portfolio_id,
    )
    print(f"target={len(portfolios)}")

    done = 0
    fail = 0

    for portfolio in portfolios:
        portfolio_id = int(portfolio["portfolio_id"])
        try:
            task_text, trouble_text = process_portfolio(portfolio)

            task_text = "\n".join(task_text)          # list[str] -> str
            trouble_text = "\n".join(trouble_text)

            task_emb = embed(task_text) if task_text.strip() else None
            trouble_emb = embed(trouble_text) if trouble_text.strip() else None

            upsert_task_vector(conn, portfolio_id, task_emb)
            upsert_trouble_vector(conn, portfolio_id, trouble_emb)

            done += 1
            if done % commit_every == 0:
                conn.commit()
                print(f"committed {done}")
            print(f"[PASS] portfolio_id={portfolio_id}") 

        except Exception as e:
            fail += 1
            conn.rollback()
            print(f"[FAIL] portfolio_id={portfolio_id} / {e}")

    conn.commit()
    print(f"done={done}, fail={fail}")


# 예시: 특정 portfolio_id 이상에서부터 N개만 처리
init_portfolio_vectors(conn, limit=100, commit_every=10, only_missing=True, start_portfolio_id=100201)
