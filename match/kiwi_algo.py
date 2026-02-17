from typing import List, Dict, Any
from psycopg.rows import dict_row
from .sub_func import psn_score_one, soft_bonus, decay_threshold, print_match_debug, highest_percent, only_top_users
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))

from db import conn


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
    """점수 합산 후 total 기준 내림차순 정렬되어 반환 (각 항목: portfolio_id, domain, task, trouble, personality, total)."""
    ranked = []
    for pid in candidates:
        domain_score = domain_scores.get(pid, 0)
        task_score = task_scores.get(pid, 0)
        trouble_score = trouble_scores.get(pid, 0)
        psn_score = psn_scores.get(pid, 0)

        total = domain_score + task_score + trouble_score + psn_score
        highest_score = highest_percent(task_score, trouble_score, psn_score)
        ranked.append({
            "portfolio_id": pid,
            "domain": domain_score,
            "task": task_score,
            "trouble": trouble_score,
            "personality": psn_score,
            "total": total,
            "highest_score" : highest_score
        })
    ranked.sort(key=lambda x: x["total"], reverse=True)
    return ranked

# 7) ptf -> user 별로 묶어서, 같은 user의 포트폴리오 total 합산

def ptf_to_user(ranked: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    ranked: [{"portfolio_id": 1, "total": 10, "highest_score": "TASK"}, ...] 
    (이미 점수 내림차순 정렬되어 있다고 가정)
    """
    if not ranked:
        return []

    # 1. DB 조회 (동일)
    portfolio_ids = [r["portfolio_id"] for r in ranked]
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT portfolio_id, user_id
            FROM portfolio
            WHERE portfolio_id = ANY(%s)
            """,
            (portfolio_ids,),
        )
        rows = cur.fetchall()
    
    pid_to_uid = {int(r["portfolio_id"]): int(r["user_id"]) for r in rows}

    # 2. 유저별 그룹핑 & 감가상각 적용
    by_user: Dict[int, Dict[str, Any]] = {}

    for r in ranked:
        pid = r["portfolio_id"]
        uid = pid_to_uid.get(pid)
        
        if uid is None:
            continue

        # [User 처음 발견 시 초기화]
        if uid not in by_user:
            by_user[uid] = {
                "user_id": uid, 
                "portfolio_ids": [], 
                "total": 0,
                # 가장 점수 높은(첫 번째) 포트폴리오의 highest_score 항목 저장
                "main_strength": r.get("highest_score", "UNKNOWN") 
            }

        # 유저별 감가상각 (현재 담긴 개수가 곧 나의 랭킹)
        current_rank = len(by_user[uid]["portfolio_ids"]) # 0, 1, 2...
        
        # 감가상각 함수 호출 (rank 0이면 100%, 1이면 80%...)
        score = decay_threshold(r["total"], current_rank)
        
        by_user[uid]["total"] += score
        by_user[uid]["portfolio_ids"].append(pid)
    
    # 3. 결과 리스트 변환 및 정렬
    result = list(by_user.values())
    
    # 최종적으로 유저 총점 순으로 다시 정렬 (User A vs User B)
    result.sort(key=lambda x: x["total"], reverse=True)
    return result



# 8) main process 함수
def main_process(post_id : int) -> list[dict[str,Any]]:
    c_post = fetch_post(conn, post_id)
    if c_post is None:
        # 이미 fetch_post에서 메시지 출력
        sys.exit(0)

    c_ptf = fetch_ptf(conn, post_id)
    if not c_ptf:
        # 이미 fetch_ptf에서 메시지 출력
        sys.exit(0)

    c_domain_scores = score_domain(conn, c_post, c_ptf)

    c_task_scores = vec_scores(
        "ptf_task_vector",
        c_post["pst_task_vector"],
        base=0,
        candidates=c_ptf,
    )
    c_trouble_scores = vec_scores(
        "ptf_trouble_vector",
        c_post["pst_trouble_vector"],
        base=0,
        candidates=c_ptf,
    )
    c_psn_scores = psn_scores(post_id, c_ptf)

    top_k = 5
    ranked = sum_score(
        c_ptf,
        c_domain_scores,
        c_task_scores,
        c_trouble_scores,
        c_psn_scores,
        top_k,
    )

    user_ranked = ptf_to_user(ranked)
    top_users = only_top_users(user_ranked, 0.3, 10)
    print(len(top_users))
    return top_users



# if __name__ == "__main__":
#     raw_post_id = input("post id를 입력하세요 : ").strip()
#     try:
#         c_post_id = int(raw_post_id)
#     except ValueError:
#         print("post id는 정수여야 합니다.")
#         sys.exit(1)

#     top_users = main_process(c_post_id)
#     print_match_debug(top_users, c_post_id)
