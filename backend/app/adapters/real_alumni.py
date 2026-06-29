"""학사지원팀 실 졸업생 데이터 공급자 (본선 진출 후 활성화).

실데이터 수령 시 작업 지점 (스펙 §5):
  1. 익명화 export → data/external/ (config.EXTERNAL_DIR)
  2. 아래 메서드에 실 컬럼 → AlumniRecord 매핑 구현 (유일한 매핑 지점)
  3. config.ALUMNI_SOURCE = "real" 로 스위치
매핑 안 되는 필드는 비워둔다(Optional → 엔진이 우아하게 후퇴).
"""

from app.adapters.alumni_types import AlumniRecord


class RealAlumniSource:
    def __init__(self) -> None:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")

    def all(self) -> list[AlumniRecord]:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")

    def list_by_department(self, department: str) -> list[AlumniRecord]:
        raise NotImplementedError("실데이터 수령 후 구현 — 스펙 §5")
