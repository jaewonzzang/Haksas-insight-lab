"""cards/syllabus — PDF 실재 시에만 경로/URL 반환 (배포 데모 우아한 강등)."""

import sqlite3

from app.cards import syllabus


def _con() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.execute(
        "CREATE TABLE course_syllabi (course_id TEXT PRIMARY KEY, overview_text TEXT, "
        "team_project TEXT, attendance_ratio REAL, presentation_ratio REAL, source_file TEXT)"
    )
    con.executemany(
        "INSERT INTO course_syllabi VALUES (?, '', 'none', 0, 0, ?)",
        [("CSE4070", "2024-020-CSE4070-01.PDF"), ("CSE3080", "2024-020-CSE3080-01.PDF"),
         ("AAT2002", "")],
    )
    return con


def test_urls_only_for_existing_files(tmp_path, monkeypatch):
    monkeypatch.setattr(syllabus, "SYLLABI_DIR", tmp_path)
    (tmp_path / "2024-020-CSE4070-01.PDF").write_bytes(b"%PDF-")
    con = _con()
    # CSE4070 파일 실재 · CSE3080 파일 없음 · AAT2002 source_file 없음 · NOPE 행 없음
    assert syllabus.urls_for(con, ["CSE4070", "CSE3080", "AAT2002", "NOPE1"]) == {
        "CSE4070": "/syllabus/CSE4070"
    }
    assert syllabus.pdf_path(con, "CSE4070") == tmp_path / "2024-020-CSE4070-01.PDF"
    assert syllabus.pdf_path(con, "CSE3080") is None
    assert syllabus.pdf_path(con, "AAT2002") is None
