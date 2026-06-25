import pandas as pd
import re

tables = pd.read_html('개설교과목정보.xls')
df = tables[0]
df.columns = df.iloc[0]
df = df.drop(0).reset_index(drop=True)

# 교양 제외
df = df[df['학과'] != '전인교육원']

# 선수과목 파싱
def parse_prereq(desc):
    if pd.isna(desc) or '선수과목' not in str(desc):
        return []
    text = str(desc).split('선수과목')[1]
    # 과목번호 패턴 추출 (예: CSE2035, AIE3050)
    codes = re.findall(r'[A-Z]{2,5}\d{3,4}', text)
    return codes

df['prereq_codes'] = df['과목 설명'].apply(parse_prereq)