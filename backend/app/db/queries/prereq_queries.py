"""course_prerequisites 관련 SELECT 묶음 (prereq_tree_json 로드)."""

import json
import sqlite3
from typing import Any, Optional


def get_prereq_tree(
    con: sqlite3.Connection, course_id: str
) -> Optional[dict[str, Any]]:
    row = con.execute(
        "SELECT prereq_tree_json FROM course_prerequisites WHERE course_id = ?",
        (course_id,),
    ).fetchone()
    return json.loads(row["prereq_tree_json"]) if row else None
