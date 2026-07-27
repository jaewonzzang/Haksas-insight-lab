# Saint+ Backend

FastAPI + raw `sqlite3` + LLM 통역기. ORM 없음. 4계층 아키텍처.

상세 모듈 책임 경계는 루트 [`CLAUDE.md`](../CLAUDE.md), [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) 참조.

## 패키지 관리: uv

```bash
# 의존성 설치 (.venv 자동 생성)
uv sync

# 새 의존성 추가
uv add <package>

# 학사지원팀 인계용 requirements.txt 변환
uv export --format requirements-txt -o requirements.txt
```

## 개발 실행 (예정)

```bash
uv run uvicorn app.main:app --reload
# → http://localhost:8000/health
# → http://localhost:8000/docs  (Swagger)
```

## 1단계 빌드

`data/raw/개설교과목정보_{2024-2,2025-1,2025-2,2026-1}.csv` → `data/processed/s_compass_courses.db`

```bash
uv run python scripts/build_course_db.py
```

스키마는 `app/db/schema.sql` 단일 정의 (6테이블 + 인덱스).

## 테스트 (예정)

```bash
uv run pytest tests/unit
uv run pytest tests/integration
```

## 디렉토리 요약

| 폴더 | 책임 |
|---|---|
| `app/api/` | HTTP 라우트만 (analyze, courses, health) |
| `app/schemas/` | Pydantic 입출력 단일 정의 |
| `app/cards/` | 카드 A/C/D 오케스트레이션 (엔진 + LLM + 어댑터 조합) |
| `app/engines/` | 정형 결과만 생산. 자연어 금지 |
| `app/llm/` | 통역만. 점수/판정 금지 |
| `app/core/` | 평가/규칙 (prereq, alias, dept_normalizer) |
| `app/parsers/` | 원본 → 구조화 |
| `app/db/` | raw sqlite3 + schema.sql + queries/ |
| `app/adapters/` | 졸업생 데이터 mock↔실 교체점 |
| `scripts/` | 1회성 오프라인 빌드 |
| `data/` | git 제외 (raw/, processed/, external/) |
| `notebooks/` | EDA·탐색용 |
| `tests/` | unit / integration |
