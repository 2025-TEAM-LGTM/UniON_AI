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
                    "You are a structured information extractor for Korean job posting documents.\n"
                    "Your sole job is to extract three categories from the given job posting text:\n"
                    "- task_items: Specific experiences and work the recruiter wants the candidate to have performed.\n"
                    "- trouble_items: Problem-solving or troubleshooting experiences the recruiter wants the candidate to have.\n"
                    "- prefer_domain_exp: Whether the posting explicitly prefers domain experience.\n\n"

                    "OUTPUT RULES:\n"
                    "- Return a single JSON object only. No explanation, no markdown, no code block, no extra text.\n"
                    "- task_items and trouble_items must be a List of strings.\n"
                    "- prefer_domain_exp must be a boolean (true / false).\n"
                    "- Output language must be Korean.\n\n"

                    "Follow the schema below exactly.\n"
                    f"OUTPUT SCHEMA:\n{SeekingExtract}\n\n"

                    "EXTRACTION RULES:\n"
                    "- task_items: Include only specific experiences and contributions the candidate is expected to have.\n"
                    "- trouble_items: Include only problem-solving, troubleshooting, or conflict-resolution experiences.\n"
                    "- prefer_domain_exp: Set true only if the text explicitly states domain experience is preferred "
                    "(e.g. '도메인 경험 우대', '해당 분야 경험자 우선'). Otherwise set false.\n"
                    "- Do NOT include job titles, role names, or tech stack listings.\n"
                    "- Use only content explicitly stated in the text. Do not infer or embellish.\n\n"

                    "INTERNAL VERIFICATION (do NOT output this process):\n"
                    "Before finalizing each extracted item, silently verify:\n"
                    "1. Is this a specific experience requirement, not just a role name or tool listing?\n"
                    "   - Role name examples to EXCLUDE: '백엔드 개발자 경험', 'PM 경험', '디자이너 경험'\n"
                    "   - Tool listing examples to EXCLUDE: 'React 사용 경험', 'Figma 활용 가능자'\n"
                    "2. Does the trouble_items entry contain a problem-solving or troubleshooting context?\n"
                    "3. Is the item 3–20 words?\n"
                    "4. For prefer_domain_exp: is domain preference EXPLICITLY stated, not implied?\n"
                    "If any check fails, discard the item or set false."
                )
            },
            {
                "role": "user",
                "content": (
                    "Extract task_items, trouble_items, and prefer_domain_exp from the [TEXT] below.\n\n"

                    "WRITING RULES:\n"
                    "- Each item should be a short phrase of approximately 3–20 words.\n"
                    "- If multiple items exist, add them as separate entries in the List.\n"
                    "- Remove duplicate or overlapping items, keeping only one.\n"
                    "- If no relevant content exists, return an empty array [].\n"
                    "- Use exactly these three keys: task_items, trouble_items, prefer_domain_exp.\n\n"

                    "FEW-SHOT EXAMPLES:\n\n"

                    "# Example 1 — all three present (개발)\n"
                    "[TEXT]: 'REST API 설계 및 개발 경험이 있으신 분을 모집합니다. "
                    "대용량 트래픽 환경에서 병목 현상을 해결해본 경험이 있으면 좋습니다. "
                    "핀테크 도메인 경험자를 우대합니다.'\n"
                    "{\"task_items\": [\"REST API 설계 및 개발 경험\"], "
                    "\"trouble_items\": [\"대용량 트래픽 환경 병목 현상 해결 경험\"], "
                    "\"prefer_domain_exp\": true}\n\n"

                    "# Example 2 — task only, no trouble, no domain preference (개발)\n"
                    "[TEXT]: 'CI/CD 파이프라인 구축 경험과 PostgreSQL 쿼리 최적화 경험이 있는 분을 찾습니다.'\n"
                    "{\"task_items\": [\"CI/CD 파이프라인 구축 경험\", \"PostgreSQL 쿼리 최적화 경험\"], "
                    "\"trouble_items\": [], "
                    "\"prefer_domain_exp\": false}\n\n"

                    "# Example 3 — role name / tool listing only → items empty (개발)\n"
                    "[TEXT]: '백엔드 개발자 경험이 있으신 분, React와 TypeScript 사용 가능하신 분을 모집합니다.'\n"
                    "{\"task_items\": [], "
                    "\"trouble_items\": [], "
                    "\"prefer_domain_exp\": false}\n\n"

                    "# Example 4 — all three present (마케팅)\n"
                    "[TEXT]: 'SNS 광고 캠페인 기획 및 집행 경험이 있으신 분을 모집합니다. "
                    "CTR 저하 원인을 분석하고 소재를 개선해본 경험이 있으면 우대합니다. "
                    "이커머스 마케팅 경험자를 우선 채용합니다.'\n"
                    "{\"task_items\": [\"SNS 광고 캠페인 기획 및 집행 경험\"], "
                    "\"trouble_items\": [\"CTR 저하 원인 분석 및 소재 개선 경험\"], "
                    "\"prefer_domain_exp\": true}\n\n"

                    "# Example 5 — task only (마케팅)\n"
                    "[TEXT]: '콘텐츠 기획 및 카피라이팅 경험, 월간 성과 리포트 작성 경험이 있는 분을 찾습니다.'\n"
                    "{\"task_items\": [\"콘텐츠 기획 및 카피라이팅 경험\", \"월간 성과 리포트 작성 경험\"], "
                    "\"trouble_items\": [], "
                    "\"prefer_domain_exp\": false}\n\n"

                    "# Example 6 — all three present (영상)\n"
                    "[TEXT]: '광고 영상 편집 및 색보정 경험이 있으신 분을 모집합니다. "
                    "촬영 현장에서 돌발 상황을 대처하고 납기를 맞춘 경험이 있으면 좋습니다. "
                    "뷰티 브랜드 영상 제작 경험자를 우대합니다.'\n"
                    "{\"task_items\": [\"광고 영상 편집 및 색보정 경험\"], "
                    "\"trouble_items\": [\"촬영 현장 돌발 상황 대처 및 납기 준수 경험\"], "
                    "\"prefer_domain_exp\": true}\n\n"

                    "# Example 7 — all three present (디자인)\n"
                    "[TEXT]: 'IA 설계 및 와이어프레임 제작 경험이 있는 분을 찾습니다. "
                    "사용자 테스트에서 발견된 UX 문제를 개선해본 경험이 있으면 우대합니다. "
                    "핀테크 앱 디자인 경험자를 우선합니다.'\n"
                    "{\"task_items\": [\"IA 설계 및 와이어프레임 제작 경험\"], "
                    "\"trouble_items\": [\"사용자 테스트 기반 UX 문제 개선 경험\"], "
                    "\"prefer_domain_exp\": true}\n\n"

                    "# Example 8 — tool listing only → items empty (디자인)\n"
                    "[TEXT]: 'Figma, Illustrator 사용 가능하신 디자이너를 모집합니다.'\n"
                    "{\"task_items\": [], "
                    "\"trouble_items\": [], "
                    "\"prefer_domain_exp\": false}\n\n"

                    "[TEXT]\n"
                    f"{seeking}"
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



