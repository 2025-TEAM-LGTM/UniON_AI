from psycopg.rows import dict_row
from pathlib import Path
import sys
from get_extract import get_t_text, get_a_text, extract_task_from_t_text, extract_task_from_a_text, extract_trouble_from_a_text, merge_tasks
from embed import embed
from put_db import upsert_task_vector, upsert_trouble_vector

BASE_DIR = Path(__file__).resolve().parents[1]  # 프로젝트 루트
sys.path.append(str(BASE_DIR))                 # db import용
from db import conn

portfolio_id= 265

def process_portfolio(portfolio: dict) -> tuple[list, list]:

    # t_text에서 task 추출
    t_text = get_t_text(portfolio)
    task_t = extract_task_from_t_text(t_text)
    print("task_t : ")
    print(task_t)
    # a_text에서 task 추출
    a_text = get_a_text(portfolio)
    task_a = extract_task_from_a_text(a_text)
    trouble = extract_trouble_from_a_text(a_text)
    print("task_a")
    print(task_a)
    print("trouble")
    print(trouble)

    # task 병합
    merged_task = merge_tasks(task_t, task_a)

    return merged_task, trouble


def fetch_one_portfolio(conn, portfolio_id: int) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT portfolio_id, t_text, a_text FROM portfolio WHERE portfolio_id = %s",
            (portfolio_id,)
        )
        return cur.fetchone()


# portfolio = fetch_one_portfolio(conn, portfolio_id)
# task_text, trouble_text = process_portfolio(portfolio)


# # task와 trouble 임베딩

# task_emb = embed(task_text) if task_text.strip() else None
# trouble_emb = embed(trouble_text) if trouble_text.strip() else None

# print("task_emb type/len:", type(task_emb), None if task_emb is None else len(task_emb))
# print("trouble_emb type/len:", type(trouble_emb), None if trouble_emb is None else len(trouble_emb))


# upsert_task_vector(conn, portfolio_id,task_emb)
# upsert_trouble_vector(conn, portfolio_id,trouble_emb)
# conn.commit()

# conn.close()