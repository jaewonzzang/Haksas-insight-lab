"""선수과목 충족도 평가.

입력: 학생 이수 course_id set + course_prerequisites.prereq_tree_json (AND/OR 트리)
출력: 충족 여부 + 미충족 노드 목록

평가 로직만 담당. 트리 자체 파싱은 parsers/prereq_parser.py.
"""

# TODO: evaluate(taken: set[str], tree: dict) -> EvaluationResult
