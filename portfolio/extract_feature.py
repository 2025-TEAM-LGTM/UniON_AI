# extract_feature.py
# OpenAI API를 사용하여 포트폴리오에서 필요한 task와 trouble만 추출하는 정보추출기
import os
import json
import re
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env") 
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _only_quoted_items(text: str) -> str:
    """
    모델 출력이 규칙을 어겨도, "..." 로 감싼 것만 최대한 회수해서
    "a","b","c" 형태로 재구성해줌.
    """
    if not text:
        return ""
    items = re.findall(r'"([^"]+)"', text)
    if not items:
        return ""
    return ",".join(f'"{it.strip()}"' for it in items if it.strip())


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
                    "너는 정보추출기다. 반드시 사용자가 요구한 출력 형식의 텍스트만 출력해라. "
                    "설명/해설/서론/마크다운/코드블록 금지."
                )
            },
            {
                "role": "user",
                "content": (
                    "아래 [본문]에서 '본인이 맡은 상세한 업무/기여'에 해당하는 내용만 뽑아라. 단순 역할은 포함하지 않는다. \n"
                    "출력 규칙:\n"
                    "1) 각 항목은 반드시 큰따옴표(\")로 감싼다.\n"
                    "2) 여러 개면 콤마(,)로만 구분한다. (예: \"A\",\"B\",\"C\")\n"
                    "3) 항목 외의 글자(설명, 접두어, 문장) 절대 출력하지 마라.\n"
                    "4) 없으면 빈 문자열만 출력하라.\n\n"
                    f"[본문]\n{t_text}"
                )
            }
        ],
    )

    out = (resp.output_text or "").strip()
    # 모델이 규칙 어기면 "..."만 회수해서 재구성
    fixed = _only_quoted_items(out)
    return fixed if fixed else ""


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
                    "너는 정보추출기다. 반드시 JSON만 출력해라. "
                    "설명/해설/마크다운/코드블록 절대 금지. "
                    "반드시 아래 키만 사용: task, trouble"
                )
            },
            {
                "role": "user",
                "content": (
                    "아래 [본문]에서 다음 두 가지를 찾아 JSON으로만 출력해.\n"
                    "1) task: '본인이 맡은 업무/기여'\n"
                    "2) trouble: '트러블슈팅/문제 해결'\n"
                    "없으면 빈 문자열.\n\n"
                    "출력 예시(이 형태 그대로):\n"
                    "{\"task\":\"...\",\"trouble\":\"...\"}\n\n"
                    f"[본문]\n{a_text}"
                )
            }
        ],
    )

    raw = (resp.output_text or "").strip()

    # 1) JSON 파싱 시도
    try:
        data = json.loads(raw)
        return {
            "task": (data.get("task") or "").strip(),
            "trouble": (data.get("trouble") or "").strip(),
        }
    except Exception:
        # 2) 파싱 실패하면: JSON처럼 보이는 부분만 잘라 재시도
        m = re.search(r'\{.*\}', raw, flags=re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(0))
                return {
                    "task": (data.get("task") or "").strip(),
                    "trouble": (data.get("trouble") or "").strip(),
                }
            except Exception:
                pass

        # 3) 최후: 그냥 빈 값 반환 (파이프라인 안 죽게)
        return {"task": "", "trouble": ""}
