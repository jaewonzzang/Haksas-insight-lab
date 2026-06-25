"""앱 설정 + 경로 상수.

런타임에 변하지 않는 경로는 여기서 단일 정의. 환경변수는 .env (예: ANTHROPIC_API_KEY).
실제 Settings 로딩(Pydantic Settings 등) 도입 여부는 OPEN_QUESTIONS 참조.
"""

from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parents[1]
DATA_DIR: Path = BASE_DIR / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
EXTERNAL_DIR: Path = DATA_DIR / "external"
MOCK_DIR: Path = DATA_DIR / "mock"
DB_PATH: Path = PROCESSED_DIR / "s_compass_courses.db"
