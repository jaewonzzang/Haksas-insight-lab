"""앱 설정 + 경로 상수.

런타임에 변하지 않는 경로는 여기서 단일 정의. 환경변수는 .env (예: ANTHROPIC_API_KEY).
실제 Settings 로딩(Pydantic Settings 등) 도입 여부는 OPEN_QUESTIONS 참조.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR: Path = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
EXTERNAL_DIR: Path = DATA_DIR / "external"
MOCK_DIR: Path = DATA_DIR / "mock"
DB_PATH: Path = PROCESSED_DIR / "s_compass_courses.db"
# 졸업생 데이터 공급자 선택. 카드 A/C(이수 이력)와 카드 D(진로)를 나눠 둔다 —
# 2차 수령 실데이터에 진로 컬럼이 없어 카드 D만 mock 유지 (OPEN_QUESTIONS A14).
ALUMNI_SOURCE: str = "real"          # 카드 A/C — "mock" | "real"
CAREER_ALUMNI_SOURCE: str = "mock"   # 카드 D — 실데이터에 진로 없음
ALUMNI_MOCK_PATH: Path = MOCK_DIR / "alumni.json"
ALUMNI_REAL_PATH: Path = PROCESSED_DIR / "alumni.json"  # build_alumni_from_enrollment 산출물

# LLM 공급자 키 (.env 에서 로드, git 제외). 미설정 시 빈 문자열.
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
