"""
강의계획서 PDF 전처리 파이프라인 (Poppler 기반)

사전 준비:
  - Poppler가 이미 설치되어 있어야 함 (PATH 확인)
  - 패키지: pip install pymupdf (선택, 페이지 정보용)
  - Tesseract는 더 이상 필요 없음

실행 (PowerShell):
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  python syllabus_parser.py --input_dir 2026_1 --output 2026_1_parsed.json
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import json
import argparse
import subprocess
import tempfile
from pathlib import Path

# Poppler 경로 (PATH에 잡혀 있으면 실행파일명만 써도 됨)
_POPPLER_BIN = r"C:\Users\김재원\AppData\Local\Microsoft\WinGet\Packages\oschwartz10612.Poppler_Microsoft.Winget.Source_8wekyb3d8bbwe\poppler-25.07.0\Library\bin"
PDFTOTEXT_PATH = _POPPLER_BIN + r"\pdftotext.exe"
PDFTOPPM_PATH = _POPPLER_BIN + r"\pdftoppm.exe"
# 이미지형 PDF OCR 폴백 (tesseract + 프로젝트 로컬 한/영 언어데이터)
TESSERACT_PATH = r"C:\msys64\mingw64\bin\tesseract.exe"
TESSDATA_DIR = str(Path(__file__).resolve().parent / "tessdata")


# ─────────────────────────────────────────
# 1. PDF → 텍스트 (Poppler -layout 모드, 이미지형은 OCR 폴백)
# ─────────────────────────────────────────

def _ocr_pdf(pdf_path: str) -> str:
    """이미지형 PDF 폴백: 페이지 렌더링(pdftoppm 300dpi) → OCR(tesseract kor+eng)."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [PDFTOPPM_PATH, "-png", "-r", "300", pdf_path, os.path.join(tmp, "p")],
            capture_output=True, check=False,
        )
        pages = []
        for png in sorted(Path(tmp).glob("p*.png")):
            r = subprocess.run(
                [TESSERACT_PATH, str(png), "stdout", "-l", "kor+eng",
                 "--tessdata-dir", TESSDATA_DIR],
                capture_output=True, check=False,
            )
            pages.append(r.stdout.decode("utf-8", errors="ignore"))
    return "\n".join(pages)


def pdf_to_text(pdf_path: str) -> str:
    """Poppler pdftotext로 표 레이아웃 유지하며 텍스트 추출. 빈 텍스트(이미지형)면 OCR 폴백."""
    result = subprocess.run(
        [PDFTOTEXT_PATH, "-layout", "-enc", "UTF-8", pdf_path, "-"],
        capture_output=True,
        check=False
    )
    text = result.stdout.decode("utf-8", errors="ignore")
    return text if text.strip() else _ocr_pdf(pdf_path)


# ─────────────────────────────────────────
# 2. 언어 감지
# ─────────────────────────────────────────

def detect_language(text: str) -> str:
    if "확장강의계획서" in text or "수업계획서" in text or "교과목 개요" in text:
        return "ko"
    if "Extended Syllabus" in text or "Course Overview" in text:
        # 한/영 양식 둘 다 "Course Overview"를 포함할 수 있음 → 한글 우선
        if "교과목 개요" in text or "선수학습내용" in text or "수업개요" in text:
            return "ko"
        return "en"
    korean_chars = len(re.findall(r"[가-힣]", text))
    return "ko" if korean_chars > 50 else "en"


# ─────────────────────────────────────────
# 3. 선수과목 추출
# ─────────────────────────────────────────

def extract_prerequisites(text: str, lang: str) -> str:
    """
    "선수학습내용" 또는 "Prerequisites" 섹션의 원문을 그대로 반환.
    빈 섹션이거나 "없음" 명시 시 빈 문자열 반환.
    """
    if lang == "ko":
        match = re.search(
            r"선수학습내용\s*\n+(.*?)(?=\n\s*\d+\.\s*수업방법|\n\s*Ⅲ\.|\n\s*3\.\s)",
            text, re.DOTALL
        )
    else:  # en
        match = re.search(
            r"(?:2\.\s*)?Prerequisites?\s*\n+(.*?)(?=\n\s*\d+\.\s*Course\s*Format|\n\s*3\.\s|\n\s*II\.)",
            text, re.DOTALL | re.IGNORECASE
        )

    if not match:
        return ""

    # 들여쓰기 공백 정리 + 빈 줄 압축
    section = match.group(1)
    lines = [l.strip() for l in section.splitlines()]
    cleaned = "\n".join(l for l in lines if l)
    return cleaned.strip()


# ─────────────────────────────────────────
# 3-1. 수업 개요 추출 (콘텐츠 유사도 신호용, 2026-07-13)
# ─────────────────────────────────────────

def extract_overview(text: str, lang: str) -> str:
    """"교과목 개요"/"수업개요"(ko) 또는 "Course Overview"(en) 섹션 본문."""
    if lang == "ko":
        match = re.search(
            r"(?:교과목 개요|수업개요)\s*\n+(.*?)(?=\n\s*\d+\.\s|\n\s*선수학습내용|\n\s*Ⅱ\.)",
            text, re.DOTALL,
        )
    else:
        match = re.search(
            r"Course\s*Overview\s*\n+(.*?)(?=\n\s*\d+\.\s|\n\s*Prerequisite|\n\s*II\.)",
            text, re.DOTALL | re.IGNORECASE,
        )
    if not match:
        return ""
    lines = [l.strip() for l in match.group(1).splitlines()]
    # 종료 경계 미매칭 시 문서 끝까지 캡처되는 것 방지 — 개요 1~2문단이면 충분
    return "\n".join(l for l in lines if l).strip()[:500]


# ─────────────────────────────────────────
# 4. 수업방법 표 파싱 (팀플 추출용)
# ─────────────────────────────────────────

def parse_course_format_table(text: str, lang: str) -> dict:
    """
    수업방법 표:
        강의   토의/토론   실험/실습   현장학습   개별/팀 별 발표   기타
         90%     10%         %         %          %             %
    각 컬럼명에 매칭되는 % 값을 dict로 반환.
    """
    result = {}

    if lang == "ko":
        # "3. 수업방법" 섹션 이후 "4. 평가방법" 이전까지
        section_match = re.search(
            r"수업방법\s*\(\%\)(.*?)(?=평가방법|\n\s*Ⅱ\.)",
            text, re.DOTALL
        )
        if not section_match:
            return result
        section = section_match.group(1)

        # 헤더 줄과 값 줄을 찾기
        # 헤더: 강의 ... 개별/팀 별 발표 ... 기타
        # 값:   90 %  10 %  ...
        header_match = re.search(
            r"(강의)\s+(토의/토론|토의.토론)\s+(실험/실습|실험.실습)\s+(현장학습)\s+(개별/팀\s*별\s*발표|개별.팀\s*별\s*발표)\s+(기타)",
            section
        )
        if not header_match:
            return result

        # 헤더 다음 줄에서 숫자 추출
        after_header = section[header_match.end():]
        # 6개의 값을 추출 (숫자 또는 빈 칸)
        # 각 값은 "XX %" 또는 그냥 "%"
        values = re.findall(r"(\d+)\s*%|(\s+)%", after_header[:300])
        # 첫 6개만 사용
        parsed_values = []
        for v in values[:6]:
            num = v[0] if v[0] else "0"
            parsed_values.append(int(num) if num.isdigit() else 0)

        if len(parsed_values) >= 6:
            keys = ["lecture", "discussion", "experiment", "field_study", "team_or_individual_presentation", "other"]
            result = dict(zip(keys, parsed_values))

    else:  # en
        section_match = re.search(
            r"Course\s*Format\s*\(\%\)(.*?)(?=Evaluation|\n\s*II\.|\n\s*4\.)",
            text, re.DOTALL | re.IGNORECASE
        )
        if not section_match:
            return result
        section = section_match.group(1)

        header_match = re.search(
            r"(Lecture)\s+(Discussion)\s+(Experiment[/\w]*)\s+(Field\s*study)\s+(Presentations?)\s+(Other)",
            section, re.IGNORECASE
        )
        if not header_match:
            return result

        after_header = section[header_match.end():]
        values = re.findall(r"(\d+)\s*%|(\s+)%", after_header[:300])
        parsed_values = []
        for v in values[:6]:
            num = v[0] if v[0] else "0"
            parsed_values.append(int(num) if num.isdigit() else 0)

        if len(parsed_values) >= 6:
            keys = ["lecture", "discussion", "experiment", "field_study", "team_or_individual_presentation", "other"]
            result = dict(zip(keys, parsed_values))

    return result


# ─────────────────────────────────────────
# 5. 평가방법 표 파싱 (출석 비율 추출용)
# ─────────────────────────────────────────

def parse_evaluation_table(text: str, lang: str) -> dict:
    """
    평가방법 표:
        중간고사  기말고사  퀴즈  발표  프로젝트  과제물  참여도  기타
         30%      35%     25%    %     %       10%    %      %
    """
    result = {}

    if lang == "ko":
        section_match = re.search(
            r"평가방법\s*\(\%\)(.*?)(?=Ⅱ\.|\n\s*교과목표|II\.)",
            text, re.DOTALL
        )
        if not section_match:
            return result
        section = section_match.group(1)

        header_match = re.search(
            r"(중간고사)\s+(기말고사)\s+(퀴즈)\s+(발표)\s+(프로젝트)\s+(과제물)\s+(참여도)\s+(기타)",
            section
        )
        if not header_match:
            return result

        after_header = section[header_match.end():]
        values = re.findall(r"(\d+)\s*%|(\s+)%", after_header[:400])
        parsed_values = []
        for v in values[:8]:
            num = v[0] if v[0] else "0"
            parsed_values.append(int(num) if num.isdigit() else 0)

        if len(parsed_values) >= 8:
            keys = ["midterm", "final", "quiz", "presentation", "project", "assignment", "participation", "other"]
            result = dict(zip(keys, parsed_values))

    else:  # en
        section_match = re.search(
            r"Evaluation\s*\(\%\)(.*?)(?=II\.|\n\s*Course\s*Objectives)",
            text, re.DOTALL | re.IGNORECASE
        )
        if not section_match:
            return result
        section = section_match.group(1)

        # 영어 양식은 컬럼 수/이름이 다를 수 있음
        # 예: Mid term exam | Final exam | Quizzes | Presentations | Projects | Assignments | Participation | Other
        header_match = re.search(
            r"(Mid[\s\-]?term[\s\w]*)\s+(Final[\s\w]*)\s+(Quizz?es?)\s+(Presentations?)\s+(Projects?)\s+(Assignments?)\s+(Participation[\w/]*)\s+(Other)",
            section, re.IGNORECASE
        )
        if not header_match:
            # 더 간단한 패턴으로 재시도
            header_match = re.search(
                r"Mid[\s\-]?term.*?Final.*?(?:Quizz?es?|Presentations?)",
                section, re.IGNORECASE | re.DOTALL
            )
            if not header_match:
                return result

        after_header = section[header_match.end():]
        values = re.findall(r"(\d+)\s*%|(\s+)%", after_header[:400])
        parsed_values = []
        for v in values[:8]:
            num = v[0] if v[0] else "0"
            parsed_values.append(int(num) if num.isdigit() else 0)

        if len(parsed_values) >= 8:
            keys = ["midterm", "final", "quiz", "presentation", "project", "assignment", "participation", "other"]
            result = dict(zip(keys, parsed_values))

    return result


# ─────────────────────────────────────────
# 6. 팀플레이 / 출석 비율 결정
# ─────────────────────────────────────────

def determine_team_project(course_format: dict, evaluation: dict, text: str) -> str:
    """
    개별/팀 별 발표 > 0 또는 Project > 0 → "required"
    "선택" 또는 "optional"이 본문에 있으면 → "optional"
    아니면 "none"
    """
    team_score = course_format.get("team_or_individual_presentation", 0)
    project_score = evaluation.get("project", 0)
    presentation_score = evaluation.get("presentation", 0)

    if team_score == 0 and project_score == 0 and presentation_score == 0:
        return "none"

    if re.search(r"선택|optional|individual or team", text, re.IGNORECASE):
        return "optional"

    if team_score > 0 or project_score > 0:
        return "required"

    if presentation_score > 0:
        # 발표만 있고 팀 명시 없으면 individual 가능성 → optional
        return "optional"

    return "none"


def get_attendance_ratio(evaluation: dict) -> float:
    """참여도 점수를 0.0~1.0으로 정규화."""
    participation = evaluation.get("participation", 0)
    return round(participation / 100, 2)


# ─────────────────────────────────────────
# 7. 과목 기본 정보 추출
# ─────────────────────────────────────────

def extract_basic_info(text: str, lang: str) -> dict:
    info = {"course_id": None, "course_name": None, "credit": None, "target_year": []}

    if lang == "ko":
        # 과목명: "과목명" 또는 헤더 줄에서
        match = re.search(r"과목명\s+([^\n]+?)\s{2,}", text)
        if match:
            # 옆 칸 헤더 "과목번호" 등 제거
            name = re.split(r"\s{2,}과목번호", match.group(1))[0].strip()
            info["course_name"] = name

        # 과목번호
        match = re.search(r"과목번호\s+([A-Z]{2,5}\d{3,4}(?:[/\-][A-Z]{2,5}\d{3,4})*)", text)
        if match:
            info["course_id"] = match.group(1).strip()

        # 학점 (구분(학점)  이론(3), 실험(0))
        match = re.search(r"이론\s*\(\s*(\d+)\s*\)", text)
        if match:
            info["credit"] = int(match.group(1))

        # 수강대상
        match = re.search(r"수강대상\s+(\d)학년", text)
        if match:
            info["target_year"] = [int(match.group(1))]
        else:
            match = re.search(r"수강대상\s+(\d)\s*[-~]\s*(\d)학년", text)
            if match:
                start, end = int(match.group(1)), int(match.group(2))
                info["target_year"] = list(range(start, end + 1))

    else:  # en
        match = re.search(r"Course\s*Title\s+([^\n]+?)\s{2,}", text, re.IGNORECASE)
        if match:
            name = re.split(r"\s{2,}(?:Semester|Course\s*Number)", match.group(1))[0].strip()
            info["course_name"] = name

        match = re.search(r"Course\s*Number\s+([A-Z]{2,5}\d{3,4}(?:[\-/]\d+)?)", text, re.IGNORECASE)
        if match:
            info["course_id"] = match.group(1).strip()

        match = re.search(r"Credit\s+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        if match:
            info["credit"] = float(match.group(1))

        match = re.search(r"Enrollment\s*Eligibility\s+([^\n]+)", text, re.IGNORECASE)
        if match:
            year_text = match.group(1).lower()
            year_map = {"freshman": 1, "1st": 1, "sophomore": 2, "2nd": 2,
                        "junior": 3, "3rd": 3, "senior": 4, "4th": 4}
            found = [v for k, v in year_map.items() if k in year_text]
            info["target_year"] = sorted(set(found))

    return info


# ─────────────────────────────────────────
# 8. 단일 PDF 처리
# ─────────────────────────────────────────

def _course_id_from_filename(name: str) -> str | None:
    """새 배치 파일명(YYYY-학기-과목코드-분반.PDF)에서 과목코드 추출. 매칭 안 되면 None → 텍스트 추출로 후퇴."""
    m = re.match(r"^\d{4}-\d{3}-([A-Z]{2,5}\d{3,4})-\d+\.pdf$", name, re.IGNORECASE)
    return m.group(1) if m else None


def parse_syllabus(pdf_path: str) -> dict:
    print(f"  처리 중: {os.path.basename(pdf_path)}")
    try:
        text = pdf_to_text(pdf_path)
        if not text.strip():
            return {"file": os.path.basename(pdf_path), "parse_error": "빈 텍스트 (PDF 추출 실패)"}

        lang = detect_language(text)
        basic = extract_basic_info(text, lang)
        fn_code = _course_id_from_filename(os.path.basename(pdf_path))
        if fn_code:
            basic["course_id"] = fn_code
        prerequisites = extract_prerequisites(text, lang)
        course_format = parse_course_format_table(text, lang)
        evaluation = parse_evaluation_table(text, lang)
        team_project = determine_team_project(course_format, evaluation, text)
        attendance_ratio = get_attendance_ratio(evaluation)

        return {
    "file": os.path.basename(pdf_path),
    "language": lang,
    **basic,
    "prerequisites_raw": prerequisites,   # ← 이름 변경
    "overview_text": extract_overview(text, lang),
    "course_format": course_format,
    "evaluation": evaluation,
    "team_project": team_project,
    "attendance_ratio": attendance_ratio,
    "presentation_ratio": round(evaluation.get("presentation", 0) / 100, 2),
    "parse_error": None
}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"file": os.path.basename(pdf_path), "parse_error": str(e)}


# ─────────────────────────────────────────
# 9. 배치 처리 메인
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="강의계획서 PDF 전처리 (Poppler 기반)")
    parser.add_argument("--input_dir", required=True)
    parser.add_argument("--output", default="syllabi_parsed.json")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    pdf_files = list(input_dir.rglob("*.pdf"))
    print(f"총 {len(pdf_files)}개 PDF 발견\n")

    results = []
    errors = []

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}]", end=" ")
        result = parse_syllabus(str(pdf_path))
        results.append(result)
        if result.get("parse_error"):
            errors.append(result["file"])

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n완료: {len(results)}개 처리")
    print(f"저장 위치: {args.output}")
    if errors:
        print(f"오류 발생 파일 ({len(errors)}개): {errors}")


if __name__ == "__main__":
    main()