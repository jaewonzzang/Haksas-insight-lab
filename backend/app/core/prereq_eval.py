"""선수과목 충족도 평가.

입력: 학생 이수 course_id set + course_prerequisites.prereq_tree_json (AND/OR 트리)
출력: 충족 여부 + 충족률(0~100) + 미충족 leaf 목록

평가 로직만 담당. 트리 자체 파싱은 parsers/prereq_parser.py.
"""

from pydantic import BaseModel


class EvaluationResult(BaseModel):
    satisfied: bool
    fulfillment: float  # 0~100. scoring.score_candidate 의 prereq_fulfillment 입력
    missing: list[str]  # 미충족 leaf 과목 코드 (OR 미충족 시 그룹 전체)


def evaluate(taken: set[str], tree: dict) -> EvaluationResult:
    fulfillment, missing = _eval_node(taken, tree)
    return EvaluationResult(
        satisfied=fulfillment >= 100.0, fulfillment=fulfillment, missing=missing
    )


def _eval_node(taken: set[str], node: dict) -> tuple[float, list[str]]:
    kind = node["type"]
    if kind == "course":
        if node["code"] in taken:
            return 100.0, []
        return 0.0, [node["code"]]
    if kind not in ("and", "or"):
        raise ValueError(f"알 수 없는 노드 타입: {kind}")
    results = [_eval_node(taken, child) for child in node["children"]]
    if kind == "and":
        fulfillment = sum(f for f, _ in results) / len(results)
        missing = [code for _, m in results for code in m]
        return fulfillment, missing
    best = max(f for f, _ in results)
    if best >= 100.0:
        return 100.0, []
    return best, [code for _, m in results for code in m]
