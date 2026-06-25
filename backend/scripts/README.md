# Offline Build Scripts

런타임 코드 경로에서 호출하지 않는 1회성 빌드 스크립트.

| 스크립트 | 입력 | 출력 |
|---|---|---|
| `build_course_db.py` | `data/raw/개설교과목정보.xls` | `data/processed/s_compass_courses.db` (5테이블) |
| `build_syllabus_index.py` | `data/raw/syllabus/*.pdf` | 벡터 인덱스 (Chroma/FAISS) |
| `generate_mock_alumni.py` | — | `data/processed/mock_alumni.{json,parquet}` |

DB는 빌드 스크립트로만 갱신. API 서버는 읽기만 한다.
