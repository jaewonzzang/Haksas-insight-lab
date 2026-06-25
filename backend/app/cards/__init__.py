"""카드 응답 오케스트레이션. engines/ + llm/translator + adapters/를 조합해 카드 A/C/D 최종 응답을 만든다.

API 핸들러(api/analyze.py)는 이 모듈만 호출하고, 엔진을 직접 import 하지 않는다.
"""
