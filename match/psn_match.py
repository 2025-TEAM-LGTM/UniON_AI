from psycopg.rows import dict_row
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))

from db import conn

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


