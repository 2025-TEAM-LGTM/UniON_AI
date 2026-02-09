from typing import Any

from psycopg.rows import dict_row
from psn_match import psn_score_one

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))

from db import conn
def soft_bonus(sim: float) -> int:
    if sim >= 0.50: return 3
    if sim >= 0.45: return 2
    if sim >= 0.40: return 1
    return 0

# 1) post_id에 대응하는 post domain + vectors 가져오기
def fetch_post(conn, post_id: int) -> dict[str, Any] | None:
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
            print(f"no post {post_id}")
            return None
        return post
        
# 2) role_id 일치 포트폴리오 id만 가져오기
def fetch_ptf(conn, post_id: int) -> list[int]:
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
        candidates = [int(r[0]) for r in cur.fetchall()]
    if not candidates:
        print("해당 포스트에서 role이 일치하는 포트폴리오가 없습니다! ")
        return []
    return candidates


# 3) domain 점수
def score_domain(conn, post: dict[str, Any], candidates: list[int]) -> dict[int, int]:
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

    return domain_scores

# 4) task/trouble 유사도 점수
def vec_scores(vector_col: str, query_vec, base: int, candidates: list[int]) -> dict[int, int]:
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
            (query_vec, candidates),
        )
        sims: dict[int, int] = {pid: 0 for pid in candidates}
        for r in cur.fetchall():
            sim = float(r["sim"])
            pid = int(r["portfolio_id"])
            score = base + soft_bonus(sim)
            # 디버깅용: 포트폴리오별 유사도/점수 출력
            # print(
            #     f"[vec_scores DEBUG] col={vector_col} portfolio_id={pid} "
            #     f"sim={sim:.4f} base={base} score={score}"
            # )
            sims[pid] = score
        return sims

# 5) personality 유사도 점수
def psn_scores( post_id : int, candidates : list[int]) -> dict[int, int]:
    scores = {}
    for pid in candidates :
        sim = (int)(psn_score_one(post_id, pid) * 5)
        scores[pid] = sim
    return scores

# 6) 점수 합산 및 정렬
def sum_score(
    candidates: list[int],
    domain_scores: dict[int, int],
    task_scores: dict[int, int],
    trouble_scores: dict[int, int],
    psn_scores: dict[int, int],
    top_k: int,
) -> list[dict[str, Any]]:
    """점수 합산 후 total 기준 내림차순 정렬된 전체 후보 리스트 반환 (각 항목: portfolio_id, domain, task, trouble, personality, total)."""
    ranked = []
    for pid in candidates:
        domain_score = domain_scores.get(pid, 0)
        task_score = task_scores.get(pid, 0)
        trouble_score = trouble_scores.get(pid, 0)
        psn_score = psn_scores.get(pid, 0)

        total = domain_score + task_score + trouble_score + psn_score
        ranked.append({
            "portfolio_id": pid,
            "domain": domain_score,
            "task": task_score,
            "trouble": trouble_score,
            "personality": psn_score,
            "total": total,
        })
    ranked.sort(key=lambda x: x["total"], reverse=True)
    return ranked


def print_match_debug(ranked: list[dict[str, Any]], post_id: int, top_k: int) -> None:
    """매칭 결과 디버깅: 각 후보의 domain/task/trouble/personality/total 점수 출력."""
    if not ranked:
        print("[DEBUG] 후보가 없습니다.")
        return
    n = len(ranked)
    print("\n" + "=" * 70)
    print(f"[매칭 디버그] post_id={post_id} | 후보 수={n} | 상위 {min(top_k, n)}개 추천")
    print("=" * 70)
    header = f"{'portfolio_id':>12} | {'domain':>6} | {'task':>6} | {'trouble':>7} | {'personality':>11} | {'total':>5}"
    print(header)
    print("-" * 70)
    for r in ranked:
        mark = "  <-- 추천" if ranked.index(r) < top_k else ""
        print(
            f"{r['portfolio_id']:>12} | {r['domain']:>6} | {r['task']:>6} | {r['trouble']:>7} | {r['personality']:>11} | {r['total']:>5}{mark}"
        )
    print("=" * 70)
    top_ids = [r["portfolio_id"] for r in ranked[:top_k]]
    print(f"추천 포트폴리오 ID (top_{top_k}): {top_ids}\n")

if __name__ == "__main__":
    raw_post_id = input("post id를 입력하세요 : ").strip()
    try:
        c_post_id = int(raw_post_id)
    except ValueError:
        print("post id는 정수여야 합니다.")
        sys.exit(1)

    c_post = fetch_post(conn, c_post_id)
    if c_post is None:
        # 이미 fetch_post에서 메시지 출력
        sys.exit(0)

    c_ptf = fetch_ptf(conn, c_post_id)
    if not c_ptf:
        # 이미 fetch_ptf에서 메시지 출력
        sys.exit(0)

    c_domain_scores = score_domain(conn, c_post, c_ptf)

    c_task_scores = vec_scores(
        "ptf_task_vector",
        c_post["pst_task_vector"],
        base=3,
        candidates=c_ptf,
    )
    c_trouble_scores = vec_scores(
        "ptf_trouble_vector",
        c_post["pst_trouble_vector"],
        base=3,
        candidates=c_ptf,
    )
    c_psn_scores = psn_scores(c_post_id, c_ptf)

    top_k = 5
    ranked = sum_score(
        c_ptf,
        c_domain_scores,
        c_task_scores,
        c_trouble_scores,
        c_psn_scores,
        top_k,
    )
    print_match_debug(ranked, c_post_id, top_k)
