"""정형 결과 → 1~2문장 자연어 변환.

규칙:
- 점수/판정/추천을 여기서 만들지 않는다.
- 정형 결과 dict + 카드 종류만 받아서 짧은 문장으로 통역.
- providers/ 의 LLM 클라이언트를 사용.
- 톤은 단정 회피 ("~할 수 있어요" 등).
"""

# TODO: translate(card_type, payload) -> str
