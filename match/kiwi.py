from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))  

from db import conn 
def soft_bonus(sim: float) -> int:
    if sim >= 0.80: return 3
    if sim >= 0.75: return 2
    if sim >= 0.70: return 1
    return 0

def kiwi_rank(conn, post_id: int, top_k: int = 50):
    register_vector(conn)

    # 1) post domain + vectors 가져오기
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
              p.post_id,
              p.prime_domain_id,
              p.second_domain_id,
              pv.pst_task_vector,
              pv.pst_trouble_vector,
              COALESCE(pv.pst_domain_exp, false) AS pst_domain_exp
            FROM post p
            JOIN post_vector pv ON pv.post_id = p.post_id
            WHERE p.post_id = %s
            """,
            (post_id,)
        )
        post = cur.fetchone()
        if not post:
            return []

    # 2) 하드필터: role_id 일치 포트폴리오 후보
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.portfolio_id
            FROM portfolio p
            JOIN post_recruit_role rr
              ON rr.role_id = p.role_id
            WHERE rr.post_id = %s
            """,
            (post_id,)
        )
        candidates = [r[0] for r in cur.fetchall()]
    if not candidates:
        return []

    # 3) domain 점수
    prime = post["prime_domain_id"]
    second = post["second_domain_id"]
    prefer = bool(post["pst_domain_exp"])

    domain_scores = {pid: 0 for pid in candidates}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT portfolio_id, domain_id
            FROM portfolio
            WHERE portfolio_id = ANY(%s)
            """,
            (candidates,)
        )
        for r in cur.fetchall():
            s = 0
            if r["domain_id"] == prime: s += 5
            if r["domain_id"] == second: s += 5
            if prefer: s += 1
            domain_scores[int(r["portfolio_id"])] = s

    # 4) task/trouble 유사도 점수 (DB에서 cosine sim = 1 - (<=>))
    def vec_scores(vector_col: str, query_vec, base: int):
        if query_vec is None:
            return {pid: 0 for pid in candidates}
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT portfolio_id, 1 - ({vector_col} <=> %s) AS sim
                FROM portfolio_vector
                WHERE portfolio_id = ANY(%s)
                  AND {vector_col} IS NOT NULL
                """,
                (query_vec, candidates)
            )
            sims = {pid: 0 for pid in candidates}
            for r in cur.fetchall():
                sim = float(r["sim"])
                sims[int(r["portfolio_id"])] = base + soft_bonus(sim)
            return sims

    task_scores = vec_scores("ptf_task_vector", post["pst_task_vector"], base=3)
    trouble_scores = vec_scores("ptf_trouble_vector", post["pst_trouble_vector"], base=3)

    # 5) 합산 + 정렬
    ranked = []
    for pid in candidates:
        total = domain_scores.get(pid, 0) + task_scores.get(pid, 0) + trouble_scores.get(pid, 0)
        ranked.append({
            "portfolio_id": pid,
            "domain": domain_scores.get(pid, 0),
            "task": task_scores.get(pid, 0),
            "trouble": trouble_scores.get(pid, 0),
            "total": total
        })
    ranked.sort(key=lambda x: x["total"], reverse=True)
    
    return [r["portfolio_id"] for r in ranked[:top_k]]

        
print(kiwi_rank(conn, 100001))