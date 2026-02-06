# UniON AI  – Feature / Vector Pipeline

UniON 프로젝트의 백엔드 텍스트 처리 및 벡터 생성 파이프라인입니다.  
포트폴리오(`portfolio`), 게시글(`post`) 텍스트에서 feature를 추출하고,  
임베딩을 생성하여 vector 테이블에 저장하는 것을 목표로 합니다.

---

## 📁 디렉토리 구조

~~~bash
├── match/ # 매칭 로직 관련
│ ├── fetch.py
│ └── kiwi_algo.py
│
├── portfolio/ # 포트폴리오 텍스트 처리
│ ├── extract_feature.py
│ ├── get_extract.py
│ ├── init_process_embed.py
│ ├── process_embed.py
│ ├── embed.py
│ └── put_db.py
│
├── post/ # 게시글 텍스트 처리
│ ├── extract_feature.py
│ ├── get_extract.py
│ ├── init_process_embed.py
│ ├── process_embed.py
│ ├── embed.py
│ └── put_db.py
│
├── sql/
│ ├── create_union_db_.sql
│ └── insert_union_db_.sql
│
├── db.py # DB 연결 설정
├── .env.example # 환경변수 예시
├── .env # 실제 환경변수 (gitignore)
├── .gitignore
└── README.md

~~~


## ⚙️ 환경 설정

### `.env` 파일 생성

`.env.example`을 참고하여 `.env` 파일을 생성합니다.

이후 DB 접속 정보 및 API Key(OpenAI 등)를 실제 값으로 채워주세요.

⚠️ .env 파일은 git에 올라가지 않습니다.

## 🚀 실행 순서 (중요)

현재 파이프라인은 vector 테이블이 먼저 채워져 있어야 이후 작업이 가능합니다.

가장 먼저 아래 파일을 실행해야 합니다.

~~~ bash
python portfolio/init_process_embed.py
python post/init_process_embed.py
~~~

해당 파일의 가장 마지막 줄에서, vector화할 id의 시작점(start_portfolio_id)와 개수 (limit)을 구할 수 있습니다. 

기존 텍스트 데이터를 불러와 임베딩을 생성하고 vector 테이블에 저장합니다

이 과정이 선행되지 않으면 이후 매칭/유사도 계산이 정상 동작하지 않습니다.


## 📌 참고 사항

portfolio / post 디렉토리는 구조를 통일하여 관리합니다.

각 디렉토리의 init_process_embed.py는 초기 1회 실행용입니다.

이후 증분 처리 로직은 process_embed.py를 기준으로 확장 예정입니다.

## 🧑‍💻 Notes

Python 3.x 기준

가상환경 사용 권장

DB 스키마는 sql/ 디렉토리 참고