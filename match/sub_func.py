from psycopg.rows import dict_row
from typing import Any, List, Dict
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))

from db import conn

#################
## personality ##
###################

def fetch_team_culture(conn, post_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT team_culture FROM post_info WHERE post_id = %s",
            (post_id,)
        )
        row = cur.fetchone()
    return row["team_culture"] or {}

def fetch_user_personality_by_portfolio(conn, portfolio_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT u.personality
            FROM portfolio pf
            JOIN users u ON u.user_id = pf.user_id
            WHERE pf.portfolio_id = %s
            """,
            (portfolio_id,)
        )
        row = cur.fetchone()
    return row["personality"] or {}

# 최대 1 최소 0
def culture_similarity(team_culture: dict, personality: dict) -> float:
    keys = set(team_culture.keys()) & set(personality.keys())
    if not keys:
        return 0.0  # 겹치는 항목 없으면 비교 불가

    matches = 0
    total = 0
    for k in keys:
        try:
            tv = int(team_culture[k])
            pv = int(personality[k])
        except Exception:
            continue
        total += 1
        if tv == pv:
            matches += 1

    return matches / total if total else 0.0

def psn_score_one(post_id : int, portfolio_id : int) -> float:
    tc = fetch_team_culture(conn, post_id)
    up = fetch_user_personality_by_portfolio(conn, portfolio_id)
    return culture_similarity(tc,up)

#################
## 점수 관련 함수들 ##
###################


def soft_bonus(sim: float) -> int:
    if sim >= 0.55: return 6
    if sim >= 0.50: return 5
    if sim >= 0.45: return 4
    if sim >= 0.40: return 3
    return 0

def decay_threshold(total : int, count : int) -> int:
    if(total <= 5) : return 0

    decay_rate = 0.8 #감가상각을 줄이고 싶다면 해당 비율을 조정할 것
    weight = decay_rate**count
    return round(weight * total)

def highest_percent(task_score : int, trouble_score : int, psn_score : int) -> str:
    scores = {
            "TASK": task_score / 6,
            "TROUBLE": trouble_score / 6,
            "PERSONALITY": psn_score / 5
        }
    return max(scores, key=scores.get)

def only_top_users(result : List[Dict[str, Any]] , percent : float, maxi : int) -> List[Dict[str, Any]]:

    if not result : return []

    cut = max(1, int(len(result) * percent)) # 최소 한명은 보장한다. 
    cut = min(maxi, cut) # 상위 percent%만큼만 출력하되, 최대 maxi를 넘지 않도록 한다. 

    cut_result = result[:cut]
    print("len:", len(result))
    print("raw cut:", int(len(result) * percent))
    print("final cut:", cut)

    # total > 0 인 사람만 남김
    return [r for r in cut_result if r.get("total", 0) > 0]

    

##### debug ##### 

def print_match_debug(user_ranked: list[dict[str, Any]], post_id: int) -> None:
    """매칭 결과 디버깅: user 단위로 합산된 추천 결과(user_id, 해당 포트폴리오 ID들, 합산 total) 출력."""
    if not user_ranked:
        print("[DEBUG] 추천 유저가 없습니다.")
        return
    n = len(user_ranked)
    print("\n" + "=" * 70)
    print(f"[매칭 디버그] post_id={post_id} | 유저 수={n} (같은 유저 포트폴리오 total 합산)")
    print("=" * 70)
    header = f"{'user_id':>10} | {'portfolio_ids':^48} | {'total':>5} | {'main_strength':>12} "
    print(header)
    print("-" * 70)

    for r in user_ranked:
        pids = r.get("portfolio_ids", [])
        pids_str = str(pids) if len(pids) <= 4 else str(pids[:3]) + ", ..."
        if len(pids_str) > 36:
            pids_str = pids_str[:33] + "..."
        print(f"{r['user_id']:>10} | {pids_str:<36} | {r['total']:>5}| {r['main_strength']:>12} ")
    print("=" * 70)
    top_user_ids = [r["user_id"] for r in user_ranked]
    print(f"추천 user_id (total 합산 순): {top_user_ids}\n")

