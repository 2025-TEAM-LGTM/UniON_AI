# extract_feature.py
# OpenAI API를 사용하여 포스트에서 task와 trouble만 추출하는 정보추출기
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


class SeekingExtract(TypedDict):
    task_items: List[str]         # ["A", "B", ...]
    trouble_items: List[str]      # ["X", "Y", ...]
    prefer_domain_exp: bool       # True/False


def openai_extract_seeking_all(seeking: str, model: str = "gpt-4o") -> SeekingExtract:
    if not seeking or not seeking.strip():
        return {"task_items": [], "trouble_items": [], "prefer_domain_exp": False}

    resp = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "너는 채용/모집 글에서 요구 경험을 추출하는 정보추출기다. "
                    "반드시 JSON만 출력한다. 설명/해설/마크다운/코드블록 금지. "
                    "아래 스키마를 정확히 따른다.\n\n"
                    f"OUTPUT SCHEMA \n {SeekingExtract}"
                )
            },
            {
                "role": "user",
                "content": (
                    "아래 [본문]에서 요구 사항을 추출해.\n\n"
                    "규칙:\n"
                    "1) task_items: '모집하는 인원이 경험해봤으면 하는 내용'만. "
                    "단순 역할/직무명(예: 백엔드 개발자, 디자이너, PM)은 절대 넣지 마.\n"
                    "2) trouble_items: '경험해봤으면 하는 문제해결/트러블슈팅'만. "
                    "단순 역할/직무명 절대 금지.\n"
                    "3) prefer_domain_exp: '해당 도메인 경험 우대/선호/우선/경험자 우대'가 명시되면 true, 아니면 false.\n"
                    "4) 각 배열 요소는 3~20단어 정도의 짧은 구문으로 쓰고, 중복은 제거해.\n"
                    "5) 반드시 JSON만 출력. 키는 정확히 task_items, trouble_items, prefer_domain_exp만 사용.\n\n"
                    "6) 아래 출력 예시는 오직 형식만 참고하고, 내용은 완전히 input만을 따를 것"
                    "출력 예시:\n"
                    "{\"task_items\":[\"REST API 설계 경험\",\"PostgreSQL 사용 경험\"],"
                    "\"trouble_items\":[\"대용량 트래픽 병목 해결 경험\"],"
                    "\"prefer_domain_exp\":true}\n\n"
                    f"[본문]\n{seeking}"
                )
            }
        ],
    )

    raw = (resp.output_text or "").strip()

    # JSON만 뽑아서 파싱 (혹시 앞뒤 군더더기 있으면 대비)
    try:
        data = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not m:
            return {"task_items": [], "trouble_items": [], "prefer_domain_exp": False}
        data = json.loads(m.group(0))

    return {
        "task_items": [s.strip() for s in (data.get("task_items") or []) if isinstance(s, str) and s.strip()],
        "trouble_items": [s.strip() for s in (data.get("trouble_items") or []) if isinstance(s, str) and s.strip()],
        "prefer_domain_exp": bool(data.get("prefer_domain_exp")),
    }



