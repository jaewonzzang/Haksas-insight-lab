-- Saint+ 1단계 산출물 DDL
-- 대상 DB: backend/data/processed/s_compass_courses.db
-- 빌드 스크립트: scripts/build_course_db.py
-- 최종 갱신: 2026-07-06
--
-- 결정 사항 요약:
--   Q2  courses 에 year, semester 추가 (NOT NULL). PK 는 course_id 단독.
--   Q3  플래그 5개 (is_english, is_cu, is_huss, is_ci, is_honors)
--       INTEGER 0|1 NOT NULL DEFAULT 0.
--   Q4  비고: remarks_raw 원문 + linked_majors_parsed JSON 배열.
--   Q5  course_aliases: id 단독 PK, UNIQUE 미부여.
--   Q6  parse_warnings.severity in {error, warning, info}.
--   Q7  매 실행 DROP TABLE IF EXISTS -> CREATE TABLE (FK 역순 DROP).
--   Q9  course_type in {regular, special, dummy}.
--       분류 로직은 적재 스크립트가 담당.
--
-- 1단계 검토 후 추가 결정:
--   is_general 복원 (courses 에 별도 플래그).
--   course_aliases.source_type 복원 (영어 enum: old_code | replacement).
--   course_aliases.condition_raw 복원 (학번/조건 원문).
--   course_restrictions.target_dept 유지 (courses.department 와 의미 구분).
--   is_huss 표기 (xls 원본 'HUSS과목' 정합).
--   course_offerings 신설 (4학기 다학기 저장, 2026-07-06).
--
-- FK 활성화는 런타임 책임 (PRAGMA foreign_keys = ON;).
-- parse_warnings 에는 FK 미정의
-- (아직 courses 에 없는 외부 코드도 기록 대상).

-- ============================================================
-- DROP (FK 의존성 역순)
-- ============================================================
DROP TABLE IF EXISTS course_categories;
DROP TABLE IF EXISTS course_offerings;
DROP TABLE IF EXISTS course_restrictions;
DROP TABLE IF EXISTS course_aliases;
DROP TABLE IF EXISTS course_prerequisites;
DROP TABLE IF EXISTS parse_warnings;
DROP TABLE IF EXISTS courses;

-- ============================================================
-- courses : 과목 마스터 (unique 과목번호 기준)
-- ============================================================
CREATE TABLE courses (
    course_id              TEXT    PRIMARY KEY,
    course_name            TEXT    NOT NULL,
    department             TEXT    NOT NULL,
    credit                 REAL,
    year                   INTEGER NOT NULL,
    semester               INTEGER NOT NULL,
    target_year_raw        TEXT,
    recommended_year_raw   TEXT,
    is_english             INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_english IN (0, 1)),
    is_cu                  INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_cu       IN (0, 1)),
    is_huss                INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_huss     IN (0, 1)),
    is_ci                  INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_ci       IN (0, 1)),
    is_honors              INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_honors   IN (0, 1)),
    course_type            TEXT    NOT NULL DEFAULT 'regular'
                                   CHECK (course_type IN (
                                       'regular', 'special', 'dummy'
                                   )),
    is_general             INTEGER NOT NULL DEFAULT 0
                                   CHECK (is_general  IN (0, 1)),
    description_raw        TEXT,
    restrictions_raw       TEXT,
    remarks_raw            TEXT,
    linked_majors_parsed   TEXT
);

-- ============================================================
-- course_offerings : 학기별 개설 여부 (최소 컬럼, 다학기 저장)
--   courses 는 latest-wins 메타데이터 1행, 개설 이력은 여기에.
--   학기별 학점/분반 변동은 추적하지 않음 (YAGNI).
-- ============================================================
CREATE TABLE course_offerings (
    course_id  TEXT    NOT NULL,
    year       INTEGER NOT NULL,
    semester   INTEGER NOT NULL CHECK (semester IN (1, 2)),
    PRIMARY KEY (course_id, year, semester),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- ============================================================
-- course_prerequisites : 선수과목 AND/OR 트리
--   콤마=AND, '또는'/'or'=OR, 괄호=OR 그룹 경계
-- ============================================================
CREATE TABLE course_prerequisites (
    course_id        TEXT PRIMARY KEY,
    prereq_raw       TEXT NOT NULL,
    prereq_tree_json TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- ============================================================
-- course_syllabi : 강의계획서 병합 속성 (개요·팀플·출석)
--   적재는 scripts/build_syllabus_prereqs.py (강의계획서 JSON 병합, 가변)
-- ============================================================
CREATE TABLE course_syllabi (
    course_id        TEXT PRIMARY KEY,
    overview_text    TEXT,
    team_project     TEXT,   -- "required" | "optional" | "none"
    attendance_ratio REAL,   -- 참여도 비중 0.0~1.0
    presentation_ratio REAL, -- 성적 발표 배점 비율 0.0~1.0
    source_file      TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- ============================================================
-- course_categories : 과목별 이수구분(성격) — (과목 × 전공) 다대다
--   과목구분표("{전공} {유형}")를 분해·정규화. 적재: scripts/build_course_categories.py.
--   major_canonical NULL = 교양/자유선택/기타 (전공 무관). 학부공통은 소속 학과로 전개.
-- ============================================================
CREATE TABLE course_categories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id       TEXT    NOT NULL,
    major_raw       TEXT,             -- 원문 전공 표기 (전공측만)
    major_canonical TEXT,             -- 정규화 학과. NULL = 교양/자유선택/기타/미매핑
    category        TEXT    NOT NULL, -- 전공입문|전공필수|전공선택|학부공통|자유선택|교양|기타|계열입학표기|미상
    area_label      TEXT              -- 교양 영역명 등 (아니면 NULL)
);

-- ============================================================
-- course_aliases : 옛 코드 / 대체과목 별칭 (단방향)
--   의미: old_* 이수 -> new_course_id 이수로 간주
-- ============================================================
CREATE TABLE course_aliases (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    new_course_id     TEXT    NOT NULL,
    old_course_id     TEXT,
    old_course_name   TEXT,
    source_type       TEXT    NOT NULL CHECK (source_type IN (
                          'old_code',
                          'replacement'
                      )),
    condition_raw     TEXT,
    raw_text          TEXT    NOT NULL,
    FOREIGN KEY (new_course_id) REFERENCES courses(course_id)
);

-- ============================================================
-- course_restrictions : 학과별 수강 제한 (4가지 정형 패턴)
-- ============================================================
CREATE TABLE course_restrictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id   TEXT    NOT NULL,
    target_dept TEXT    NOT NULL,
    status      TEXT    NOT NULL CHECK (status IN (
                    'allowed',
                    'forbidden',
                    'major_only_allowed',
                    'major_only_forbidden'
                )),
    raw_text    TEXT    NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- ============================================================
-- parse_warnings : 빌드 시 모호/실패 케이스 로그
--   course_id NULL 허용 (특정 과목 무관한 일반 경고용)
--   FK 미정의 (적재 중 아직 courses 에 없는 외부 코드도 기록 대상)
--   field 자유 토큰 ('prerequisites', 'aliases', 'restrictions',
--   'multi_section', 'course_type' 등)
-- ============================================================
CREATE TABLE parse_warnings (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id  TEXT,
    field      TEXT    NOT NULL,
    severity   TEXT    NOT NULL CHECK (severity IN (
                   'error', 'warning', 'info'
               )),
    issue      TEXT    NOT NULL,
    raw_text   TEXT
);

-- ============================================================
-- 인덱스
-- ============================================================
CREATE INDEX idx_courses_department       ON courses(department);
CREATE INDEX idx_courses_course_type      ON courses(course_type);
CREATE INDEX idx_courses_is_general       ON courses(is_general);
CREATE INDEX idx_offerings_year_sem       ON course_offerings(year, semester);
CREATE INDEX idx_restrictions_course      ON course_restrictions(course_id);
CREATE INDEX idx_restrictions_target_dept ON course_restrictions(target_dept);
CREATE INDEX idx_aliases_new              ON course_aliases(new_course_id);
CREATE INDEX idx_aliases_old              ON course_aliases(old_course_id);
CREATE INDEX idx_warnings_severity        ON parse_warnings(severity);
CREATE INDEX idx_warnings_course          ON parse_warnings(course_id);
CREATE INDEX idx_categories_course        ON course_categories(course_id);
CREATE INDEX idx_categories_major         ON course_categories(major_canonical);
