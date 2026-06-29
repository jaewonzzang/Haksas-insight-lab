"""합성 mock 졸업생 데이터 공급자 (개발 단계 기본값).

scripts/generate_mock_alumni.py 산출물(JSON, AlumniRecord[]) 을 로드.
스키마는 실데이터 합의 전까지 잠정.
"""

import json
from pathlib import Path

from app.adapters.alumni_types import AlumniRecord


class MockAlumniSource:
    def __init__(self, path: Path) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._records = [AlumniRecord.model_validate(r) for r in raw]

    def all(self) -> list[AlumniRecord]:
        return list(self._records)

    def list_by_department(self, department: str) -> list[AlumniRecord]:
        return [r for r in self._records if r.department == department]
