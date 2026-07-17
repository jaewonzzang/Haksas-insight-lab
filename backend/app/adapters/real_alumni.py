"""학사지원팀 실 수강내역 기반 졸업생 데이터 공급자.

scripts/build_alumni_from_enrollment.py 산출물(JSON, AlumniRecord[]) 을 로드.
원본에 진로 컬럼이 없어 career 는 전부 None — 카드 D 는 UNLABELED 로 후퇴한다
(docs/OPEN_QUESTIONS.md A14). 카드 A 코호트/카드 C 전공 분포는 실데이터로 동작.
"""

import json
from pathlib import Path

from app.adapters.alumni_types import AlumniRecord


class RealAlumniSource:
    def __init__(self, path: Path) -> None:
        if not Path(path).exists():
            raise FileNotFoundError(
                f"실 졸업생 데이터 없음: {path} — scripts/build_alumni_from_enrollment.py 먼저 실행"
            )
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self._records = [AlumniRecord.model_validate(r) for r in raw]

    def all(self) -> list[AlumniRecord]:
        return list(self._records)

    def list_by_department(self, department: str) -> list[AlumniRecord]:
        return [r for r in self._records if r.department == department]
