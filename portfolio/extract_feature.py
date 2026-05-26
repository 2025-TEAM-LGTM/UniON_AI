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
                "You are a structured information extractor for Korean portfolio documents.\n"
                "Your sole job is to extract one category from the given portfolio text:\n"
                "- task: Specific actions, work, and contributions the AUTHOR personally performed.\n\n"

                "OUTPUT RULES:\n"
                "- Return a single JSON object only. No explanation, no markdown, no code block, no extra text.\n"
                "- Each value must be a List of strings.\n"
                "- Output language must be Korean.\n\n"

                "Follow the schema below exactly.\n"
                f"OUTPUT SCHEMA:\n{SeekingExtract_t}\n\n"

                "EXTRACTION RULES:\n"
                "- task: Include only specific actions, work, and contributions directly performed by the author.\n"
                "- Do NOT include job titles, role names, or tech stack listings.\n"
                "- Use only content explicitly stated in the text. Do not infer or embellish.\n"
                "- Include only what the AUTHOR did, not what the team or company did.\n\n"

                "INTERNAL VERIFICATION (do NOT output this process):\n"
                "Before finalizing each extracted item, silently verify:\n"
                "1. Is the subject of this action clearly the AUTHOR (not the team or company)?\n"
                "   - Signals of author action: '제가', '저는', '직접', '담당했습니다', '구현했습니다'\n"
                "   - Signals of team action: '팀에서', '팀이', '함께', '우리가' → EXCLUDE unless author's personal role is specified\n"
                "2. Is the item 3–20 words and free of role names or stack listings?\n"
                "If any check fails, discard the item."
            )
        },
        {
            "role": "user",
            "content": (
                "Extract task from the [TEXT] below.\n\n"

                "WRITING RULES:\n"
                "- Each item should be a short phrase of approximately 3–20 words.\n"
                "- If multiple items exist, add them as separate entries in the List.\n"
                "- Remove duplicate or overlapping items, keeping only one.\n"
                "- If no relevant content exists, return an empty array [].\n\n"

                "FEW-SHOT EXAMPLES:\n\n"

                "# Example 1 — task present (개발)\n"
                "[TEXT]: '데이터 전처리 파이프라인을 설계하고 REST API를 개발했습니다. "
                "또한 CI/CD 파이프라인을 직접 구축했습니다.'\n"
                "{\"task\": [\"데이터 전처리 파이프라인 설계\", \"REST API 개발\", \"CI/CD 파이프라인 직접 구축\"]}\n\n"

                "# Example 2 — team action vs author action (개발)\n"
                "[TEXT]: '팀에서 마이크로서비스 아키텍처를 도입했고, 저는 서비스 간 통신 모듈을 직접 구현했습니다.'\n"
                "{\"task\": [\"서비스 간 통신 모듈 직접 구현\"]}\n\n"

                "# Example 3 — task present (마케팅)\n"
                "[TEXT]: '신규 앱 출시를 위해 제가 직접 SNS 광고 캠페인을 기획하고 집행했습니다. "
                "또한 월간 성과 리포트를 작성해 팀에 공유했습니다.'\n"
                "{\"task\": [\"SNS 광고 캠페인 기획 및 집행\", \"월간 성과 리포트 작성 및 공유\"]}\n\n"

                "# Example 4 — task present (영상)\n"
                "[TEXT]: '30초 브랜드 광고의 편집을 제가 단독으로 맡았습니다. "
                "인터뷰 장면의 자막 작업과 사운드 믹싱을 담당했습니다.'\n"
                "{\"task\": [\"30초 브랜드 광고 단독 편집\", \"인터뷰 장면 자막 작업\", \"사운드 믹싱 담당\"]}\n\n"

                "# Example 5 — task present (디자인)\n"
                "[TEXT]: '앱 리디자인 프로젝트에서 제가 IA 설계와 와이어프레임 제작을 맡았습니다. "
                "사용자 테스트 시나리오도 직접 작성했습니다.'\n"
                "{\"task\": [\"IA 설계 및 와이어프레임 제작\", \"사용자 테스트 시나리오 직접 작성\"]}\n\n"

                "[TEXT]\n"
                f"{t_text}"
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
                    "You are a structured information extractor for Korean portfolio documents.\n"
                    "Your sole job is to extract two categories from the given portfolio text:\n"
                    "- task: Specific actions, work, and contributions the AUTHOR personally performed.\n"
                    "- trouble: Problems, constraints, errors, conflicts, or performance issues encountered, "
                    "including resolution attempts and outcomes.\n\n"

                    "OUTPUT RULES:\n"
                    "- Return a single JSON object only. No explanation, no markdown, no code block, no extra text.\n"
                    "- Each value must be a List of strings.\n"
                    "- Output language must be Korean.\n\n"

                    "Follow the schema below exactly.\n"
                    f"OUTPUT SCHEMA:\n{SeekingExtract_a}\n\n"

                    "EXTRACTION RULES:\n"
                    "- task: Include only specific actions, work, and contributions directly performed by the author.\n"
                    "- trouble: Include only problem situations, constraints, errors, conflicts, performance issues "
                    "and their resolution attempts or outcomes.\n"
                    "- Do NOT include job titles, role names, or tech stack listings.\n"
                    "- Use only content explicitly stated in the text. Do not infer or embellish.\n"
                    "- Include only what the AUTHOR did, not what the team or company did.\n\n"

                    "INTERNAL VERIFICATION (do NOT output this process):\n"
                    "Before finalizing each extracted item, silently verify:\n"
                    "1. Is the subject of this action clearly the AUTHOR (not the team or company)?\n"
                    "   - Signals of author action: '제가', '저는', '직접', '담당했습니다', '구현했습니다'\n"
                    "   - Signals of team action: '팀에서', '팀이', '함께', '우리가' → EXCLUDE unless author's personal role is specified\n"
                    "2. Is the item 3–20 words and free of role names or stack listings?\n"
                    "If any check fails, discard the item."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extract task and trouble from the [TEXT] below.\n\n"

                    "WRITING RULES:\n"
                    "- Clearly distinguish between task and trouble.\n"
                    "- If multiple items exist, add them as separate entries in the List.\n"
                    "- Remove duplicate or overlapping items, keeping only one.\n"
                    "- If no relevant content exists, return an empty array [].\n\n"

                    "FEW-SHOT EXAMPLES:\n\n"

                    "FEW-SHOT EXAMPLES:\n\n"

                    "# Example 1 — task and trouble both present (개발)\n"
                    "[TEXT]: '사용자 급증으로 API 응답이 5초 이상 지연되어, 제가 직접 쿼리 최적화와 "
                    "Redis 캐싱을 도입해 1초 이내로 개선했습니다. 또한 CI/CD 파이프라인을 직접 구축했습니다.'\n"
                    "{\"task\": [\"CI/CD 파이프라인 직접 구축\"], "
                    "\"trouble\": [\"API 응답 5초 이상 지연 문제를 Redis 캐싱 도입으로 1초 이내 개선\"]}\n\n"

                    "# Example 2 — task only, no trouble (개발)\n"
                    "[TEXT]: '데이터 전처리 파이프라인을 설계하고 REST API를 개발했습니다.'\n"
                    "{\"task\": [\"데이터 전처리 파이프라인 설계\", \"REST API 개발\"], \"trouble\": []}\n\n"

                    "# Example 3 — team action vs author action (개발)\n"
                    "[TEXT]: '팀에서 마이크로서비스 아키텍처를 도입했고, 저는 서비스 간 통신 모듈을 직접 구현했습니다.'\n"
                    "{\"task\": [\"서비스 간 통신 모듈 직접 구현\"], \"trouble\": []}\n\n"

                    "# Example 4 — task and trouble both present (마케팅)\n"
                    "[TEXT]: '신규 앱 출시를 위해 제가 직접 SNS 광고 캠페인을 기획하고 집행했습니다. "
                    "초기 CTR이 0.8%로 목표치를 밑돌아, A/B 테스트를 통해 카피와 소재를 교체한 결과 CTR 2.1%로 개선했습니다.'\n"
                    "{\"task\": [\"SNS 광고 캠페인 기획 및 집행\"], "
                    "\"trouble\": [\"CTR 0.8% 미달 문제를 A/B 테스트 기반 소재 교체로 2.1%까지 개선\"]}\n\n"

                    "# Example 5 — task and trouble both present (영상)\n"
                    "[TEXT]: '30초 브랜드 광고의 편집을 제가 단독으로 맡았습니다. "
                    "촬영본 색감이 레퍼런스와 달라 색 보정 작업을 직접 수행해 톤을 통일했고, "
                    "최종본 납품 기한을 맞췄습니다.'\n"
                    "{\"task\": [\"30초 브랜드 광고 단독 편집\", \"색 보정 작업 직접 수행\"], "
                    "\"trouble\": [\"촬영본 색감 불일치 문제를 직접 색 보정으로 톤 통일\"]}\n\n"

                    "# Example 6 — team action vs author action (영상)\n"
                    "[TEXT]: '팀이 함께 다큐멘터리를 제작했으며, 저는 인터뷰 장면의 자막 작업과 "
                    "사운드 믹싱을 담당했습니다.'\n"
                    "{\"task\": [\"인터뷰 장면 자막 작업\", \"사운드 믹싱 담당\"], \"trouble\": []}\n\n"

                    "# Example 7 — task and trouble both present (디자인)\n"
                    "[TEXT]: '앱 리디자인 프로젝트에서 제가 IA 설계와 와이어프레임 제작을 맡았습니다. "
                    "사용자 테스트 결과 네비게이션 혼란 문제가 발견되어, 메뉴 구조를 재설계해 "
                    "태스크 완료율을 68%에서 89%로 향상시켰습니다.'\n"
                    "{\"task\": [\"IA 설계 및 와이어프레임 제작\"], "
                    "\"trouble\": [\"네비게이션 혼란 문제를 메뉴 구조 재설계로 태스크 완료율 89%로 향상\"]}\n\n"

                    "[TEXT]\n"
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

