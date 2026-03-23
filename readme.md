# UniON Matching – Feature / Vector / 매칭 파이프라인

UniON 프로젝트의 **텍스트 처리 → 벡터 저장 → 매칭 API** 파이프라인입니다.  
포트폴리오·게시글(post) 텍스트에서 feature를 추출하고 임베딩을 생성해 vector 테이블에 저장한 뒤, **post_id 기준으로 적합한 유저(포트폴리오)를 매칭**하여 API로 제공합니다.

---

## 📁 디렉토리 구조

```text
uniON_matching/
├── db.py                    # DB 연결 (PostgreSQL + pgvector)
├── match_server.py          # FastAPI 서버: post_id → 매칭 결과 JSON
│
├── match/                   # 매칭 로직
│   ├── kiwi_algo.py         # 메인 매칭: fetch → domain/task/trouble/personality 점수 → user 단위 합산·정렬
│   └── sub_func.py          # personality 유사도, soft_bonus, decay, only_top_users, print_match_debug
│
├── portfolio/               # 포트폴리오 텍스트 → 벡터
│   ├── extract_feature.py   # t_text / a_text에서 task·trouble 추출 (OpenAI)
│   ├── get_extract.py       # get_t_text, get_a_text, extract_*, merge_tasks
│   ├── process_embed.py     # process_portfolio: 추출 → (merged_task, trouble)
│   ├── embed.py             # 텍스트 → 임베딩 벡터
│   ├── put_db.py            # portfolio_vector 테이블 upsert (task/trouble 벡터)
│   └── init_process_embed.py # 일괄 초기화: fetch_portfolios → process → embed → put_db
│
├── post/                    # 게시글(seeking) 텍스트 → 벡터
│   ├── extract_feature.py   # seeking에서 task/trouble/prefer 추출 (OpenAI)
│   ├── get_extract.py       # (필요 시) 래퍼
│   ├── process_embed.py     # process_post: seeking → task, trouble, prefer
│   ├── embed.py             # 텍스트 → 임베딩 벡터 
│   ├── put_db.py            # post_vector 테이블 upsert
│   └── init_process_embed.py # 일괄 초기화: fetch_posts → process → embed → put_db
│
├── sql/
│   ├── create_uniON_db_ver.3.sql   # DB 스키마 (vector, portfolio, post, post_vector, portfolio_vector 등)
│   ├── insert_uniON_db_ver3.sql
│   └── insert_portfolio.sql
│
├── .env.example             # 환경 변수 예시
├── .env                     # 실제 값 (git 제외)
└── README.md
```

---

## 🔄 전체 흐름 요약

1. **벡터 준비 (선행)**  
   `portfolio/init_process_embed.py`, `post/init_process_embed.py`로  
   portfolio / post 텍스트에서 feature 추출 → 임베딩 생성 → `portfolio_vector`, `post_vector` 테이블에 저장.

2. **매칭 요청 시**  
   `match_server`가 `post_id`를 받으면 `match.kiwi_algo.main_process(post_id)`를 호출.

3. **매칭 파이프라인 (`kiwi_algo`)**  
   - **fetch_post**: 해당 post의 domain, task/trouble 벡터, 선호 정보 조회  
   - **fetch_ptf**: post의 recruit role_id와 일치하는 portfolio_id 목록 조회  
   - **score_domain**: prime/second domain 일치 점수  
   - **vec_scores**: post의 task/trouble 벡터와 portfolio 벡터 유사도 → task/trouble 점수  
   - **psn_scores**: post의 team_culture와 유저 personality 유사도 (sub_func)  
   - **sum_score**: domain + task + trouble + personality 합산, 상위 top_k개 포트폴리오  
   - **ptf_to_user**: 같은 user의 여러 포트폴리오를 묶고, 감가상각 적용 후 user별 total 합산  
   - **only_top_users**: 상위 일정 비율·최대 인원만 반환, 각 항목에 `user_id`, `main_strength` 등 포함  

4. **API 응답**  
   `POST /match_result` → `{ "results": [ { "user_id", "main_strength" }, ... ] }`

---

## ⚙️ 환경 설정

### 1. `.env` 파일

`.env.example`을 복사해 `.env`를 만들고, DB·OpenAI 값을 채웁니다.

```bash
cp .env.example .env
```

필요 변수 예시:

- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `OPENAI_API_KEY` (feature 추출·임베딩용)

`.env`는 버전 관리에 포함하지 않습니다.

### 2. DB 스키마

`sql/create_uniON_db_ver.3.sql`로 PostgreSQL에 스키마를 생성하고, `vector` 확장(pgvector)이 켜져 있어야 합니다.

### 3. Python

- Python 3.x  
- 가상환경 사용 권장  
- 의존 패키지: `psycopg`, `pgvector`, `openai`, `python-dotenv`, `fastapi`, `pydantic` 등 (requirements.txt 있다면 해당 기준)

---

## 🚀 실행 순서

### 1. 벡터 테이블 채우기 (필수 선행)

매칭은 `portfolio_vector`, `post_vector`가 채워진 상태에서만 동작합니다.

```bash
# 포트폴리오: t_text, a_text → task/trouble 추출 → 임베딩 → portfolio_vector
python portfolio/init_process_embed.py

# 게시글: seeking → task/trouble/prefer 추출 → 임베딩 → post_vector
python post/init_process_embed.py
```

각 스크립트 **맨 아래**에서 다음을 조절할 수 있습니다.

- **시작 ID**: `start_portfolio_id` / `start_post_id` (해당 ID 이상만 처리)
- **개수**: `limit`
- **대상**: `only_missing=True`면 벡터가 비어 있거나 NULL인 행만 처리

이 단계가 끝나야 매칭/유사도 계산이 정상 동작합니다.

### 2. 매칭 API 서버 실행

```bash
# 프로젝트 루트에서
uvicorn server:app --reload
```

- **통신 확인**: `POST /ping` body `{ "post_id": 123 }`  
- **매칭 결과**: `POST /match_result` body `{ "post_id": 123 }`  
  → 응답: `{ "results": [ { "user_id": 1, "main_strength": "TASK" }, ... ] }`

---

## 📌 참고 사항

- **portfolio / post** 디렉토리는 역할이 대칭으로 구성되어 있습니다 (extract → process → embed → put_db → init).
- **init_process_embed.py**는 초기·일괄 벡터화용입니다. 이후 증분 갱신은 `process_embed` 기반으로 확장할 수 있습니다.
- **매칭 결과**는 포트폴리오 단위가 아니라 **user 단위**로, 같은 유저의 여러 포트폴리오 점수를 감가상각 적용 후 합산해 상위 유저만 반환합니다.
- **main_strength**는 task / trouble / personality 중 가장 비중이 큰 항목을 나타냅니다 (sub_func의 `highest_percent`).
