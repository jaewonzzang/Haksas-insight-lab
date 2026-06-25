"""1단계 산출물 빌드: 개설교과목정보.xls → s_compass_courses.db.

오프라인 1회성 스크립트. API 서버 코드 경로에서 호출 금지.
parsers/* 를 조합해 5테이블 (courses, course_prerequisites, course_aliases,
course_restrictions, parse_warnings)을 채운다.

usage: python scripts/build_course_db.py [--xls PATH] [--db PATH]
"""

# TODO: main()
