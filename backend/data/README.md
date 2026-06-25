# Data 자산

`.gitignore`에 의해 실제 데이터 파일은 git에서 제외된다. 디렉토리 구조만 `.gitkeep`으로 유지.

| 폴더 | 내용 |
|---|---|
| `raw/` | 원본 외부 파일 (`개설교과목정보.xls`, 강의계획서 PDF 등). 절대 손대지 않음 |
| `processed/` | 파싱/빌드 산출물 (`s_compass_courses.db`, 벡터 인덱스 등). `scripts/build_*`로만 갱신 |
| `external/` | 학사지원팀 실데이터 수령 자리 (졸업생 익명화 데이터). 본선 진출 후 채워짐 |
| `mock/` | 합성 mock 데이터 (`scripts/generate_mock_alumni.py` 산출물). 실데이터 도착 전 개발/시연용 |

## 정책

- 데이터를 런타임에 재생성하지 않는다. `scripts/build_*.py` / `generate_mock_alumni.py` 로만 갱신.
- 어댑터(`app/adapters/`)가 `mock/` ↔ `external/` 교체점. 호출부는 어댑터 Protocol만 의존.
- 실제 `.gitignore` 패턴은 첫 데이터 추가 시점에 잠근다.
