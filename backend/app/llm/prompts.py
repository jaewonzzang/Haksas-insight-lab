"""프롬프트 템플릿 모음. 단일 파일 정책.

각 카드/상황별 템플릿을 모듈 상수(dict[str, str])로 정의. 외부 파일 분리하지 않음.
"""

CARD_A_REASON: str = ""  # TODO: 추천 사유 1줄 통역 프롬프트
CARD_D_PATTERN: str = ""  # TODO: 유사 졸업생 진로 패턴 1단락 통역
WHY_EXPLANATION: str = ""  # TODO: "왜?" 패널 본문 (학사 시스템 원문 인용 포함)
