# extract_feature.py
# OpenAI API를 사용하여 포트폴리오에서 필요한 task와 trouble만 추출하는 정보추출기
import os
import json
import re
from typing import TypedDict, List
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env") 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SeekingExtract_t(TypedDict):
    task : List[str]

class SeekingExtract_a(TypedDict):
    task : List[str]
    troulbe : List[str]


# -----------------------------
# for t_text: task만 "문자열"로 반환
# -----------------------------
def openai_extract_task(t_text: str, model: str = "gpt-4o") -> str:
    """
    t_text에서 '본인이 맡은 업무/역할/기여'만 추출해서
    반드시 다음 형식의 "문자열"만 반환:
      - 한 개:  "..."
      - 여러 개: "..." , "..." , "..."
      - 없으면: (빈 문자열)
    """
    if not t_text or not t_text.strip():
        return ""

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "너는 포트폴리오에서 경험을 추출하는 정보추출기다."
                    "반드시 문자열의 List로만 출력한다. 설명/해설/서론/마크다운/코드블록 금지."
                    "아래 스키마를 정확히 따른다.\n\n"
                    f"OUTPUT SCHEMA \n {SeekingExtract_t}"
                )
            },
            {
                "role": "user",
                "content": (
                    "아래 [본문]에서 '본인이 맡은 상세한 업무/기여'에 해당하는 내용만 뽑아라."
                    "단순 역할/직무명(예: 백엔드 개발자, 디자이너, PM)은 절대 넣지 마."
                    "해당 역할 또는 직무에서 경험해본 업무를 적는다."
                    "각 배열 요소는 3~20단어 정도의 짧은 구문으로 쓰고, 중복은 제거해.\n"
                    "아래 출력 예시는 오직 형식만 참고하고, 내용은 완전히 input만을 따를 것"
                    "출력 규칙:\n"
                    "{\"task\":[\"이용자 리뷰와 통계 자료 조사\",\"영상과 카드뉴스 제작\"]}"
                    f"[본문]\n{t_text}"
                )
            }
        ],
    )

    out = (resp.output_text or "").strip()

        # JSON만 뽑아서 파싱 (혹시 앞뒤 군더더기 있으면 대비)
    try:
        data = json.loads(out)
    except Exception:
        m = re.search(r"\{.*\}", out, flags=re.DOTALL)
        if not m:
            return {"task": []}
        data = json.loads(m.group(0))


    return {
        "task": [s.strip() for s in (data.get("task") or []) if isinstance(s, str) and s.strip()]
    }


# -----------------------------
# for a_text: task, trouble 둘 다 뽑아서 dict 반환
# (response_format 없이 JSON 강제 + 파싱)
# -----------------------------
def openai_extract_task_and_trouble(a_text: str, model: str = "gpt-4o") -> dict:
    """
    a_text에서 task/trouble을 뽑아 dict로 반환:
      {"task": "...", "trouble": "..."}
    - 없으면 빈 문자열
    - JSON 파싱 실패해도 최대한 복구 시도
    """
    if not a_text or not a_text.strip():
        return {"task": "", "trouble": ""}

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "너는 포트폴리오 본문에서 "
                    "본인이 실제로 수행한 업무(task)와 "
                    "② 그 과정에서 발생한 문제 및 해결 경험(trouble)을 추출하는 정보추출기다.\n\n"
                    "출력은 반드시 JSON 하나만 반환한다.\n"
                    "설명, 해설, 서론, 마크다운, 코드블록, 추가 텍스트는 절대 출력하지 않는다.\n"
                    "각 값은 문자열의 List 형태여야 한다.\n\n"
                    "아래 스키마를 정확히 따른다.\n"
                    f"OUTPUT SCHEMA \n {SeekingExtract_a}"

                    "추출 기준:\n"
                    "- task: 직접 수행한 구체적인 행동, 작업, 기여 내용만 포함한다.\n"
                    "- trouble: 문제 상황, 제약, 오류, 갈등, 성능 이슈와 그 해결 시도/결과만 포함한다.\n"
                    "- 단순 직무명, 역할명, 기술 스택 나열은 포함하지 않는다.\n"
                    "- 추론이나 각색 없이, 본문에 명시된 내용만 사용한다."                    
                )
            },
            {
                "role": "user",
                "content": (
                    "아래 [본문]기반으로 task와 trouble을 추출하라..\n"
                    "작성 규칙:\n"
                    "- task와 trouble은 명확히 구분한다.\n"
                    "- 각 항목은 3~20단어 내외의 짧은 구문으로 작성한다.\n"
                    "- 여러 항목의 경우, List에 쉼표로 구분하여 추가한다. "
                    "- 의미가 겹치는 항목은 하나만 남기고 제거한다.\n"
                    "- 해당되는 내용이 없으면 빈 배열([])로 반환한다.\n\n"
                    "출력 형식 예시 (형식만 참고):\n"
                    "{\"task\": [\"데이터 전처리 파이프라인 설계\"], "
                    "\"trouble\": [\"대용량 데이터 처리 중 메모리 초과 문제 해결\", "
                    "\"API 응답 지연 현상 원인 분석 및 개선\", "
                    "\"모델 예측 결과 편향 문제 조정\"]}"


                    "[본문]\n"
                    f"{a_text}"
                )
            }
        ],
    )

    out = (resp.output_text or "").strip()

    # 1) JSON 파싱 시도
    try:
        data = json.loads(out)

    except Exception:
        # 2) 파싱 실패하면: JSON처럼 보이는 부분만 잘라 재시도
        m = re.search(r'\{.*\}', out, flags=re.DOTALL)
        if not m:
            return {"task": [], "trouble": []}
        data = json.loads(m.group(0))


    return {
        "task": [s.strip() for s in (data.get("task") or []) if isinstance(s, str) and s.strip()],
        "trouble": [s.strip() for s in (data.get("trouble") or []) if isinstance(s, str) and s.strip()]
    }

