"""강의계획서 PDF → 구조화 필드.

추출 필드: course_id, course_name, credit, target_year, prerequisites_raw,
           course_format, evaluation, team_project, attendance_ratio.

추출 방식: Poppler pdftotext -layout (Tesseract OCR은 표 깨짐으로 사용 불가).
사용자 로컬에 동작 검증된 syllabus_parser.py 가 있음 → 이식 예정.
"""

# TODO: parse(pdf_path) -> SyllabusRow
