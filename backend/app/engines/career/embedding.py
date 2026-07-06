"""이수경로 임베딩: 과목 ID TF-IDF (A10 확정 — mock 단계).

문서 = 졸업생 1명의 이수 course_id 집합을 공백 결합한 문자열.
실데이터 수령 후 표현(설명 임베딩 등) 재검토 — OPEN_QUESTIONS A10 잔여.
"""

from typing import Iterable, Optional, Sequence, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer


def _doc(courses: Iterable[str]) -> str:
    return " ".join(sorted(courses))


def embed_sets(
    alumni_course_sets: Sequence[Iterable[str]],
    student_courses: Iterable[str],
) -> Optional[Tuple[object, object]]:
    docs = [_doc(s) for s in alumni_course_sets]
    if not any(docs):
        return None
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(docs)
    student = vectorizer.transform([_doc(student_courses)])
    return matrix, student
