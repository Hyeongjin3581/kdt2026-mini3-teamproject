# [개인 보완] 회고 ① 크롤링 확장 — A안 (2) 관련 기사 거르기 + 본문 수집
# 실행: 저장소 최상위에서 python "개선/04_크롤링확장/02_본문수집.py"
#
# 팀 D는 보도자료 본문이 첨부파일(hwpx/pdf)에만 있어 제목+요약으로만 분류했다.
# 여기서는 첨부파일을 내려받아 글자를 뽑는다 (PDF 우선, 없으면 HWPX). 정책뉴스는 본문(div.view_cont)을 읽는다.
#   - PDF: pymupdf 로 글자 추출 / HWPX: zip 안의 Contents/section*.xml 에서 글자(<hp:t>) 추출
#   - 원본 파일은 저장하지 않고 글자만 CSV 로 남긴다 (저장소 용량·저작권 고려)

import io
import re
import time
import zipfile
import requests
import pymupdf
import pandas as pd
from bs4 import BeautifulSoup

출력 = '개선/04_크롤링확장'
헤더 = {'User-Agent': 'Mozilla/5.0 (KDT student research project)'}

목록 = pd.read_csv(f'{출력}/정책브리핑_수집_2015_2025.csv').drop_duplicates('링크').reset_index(drop=True)
print('중복 제거 후:', len(목록))

# 1차 필터 (팀 D 4-2와 같은 규칙): 제목에 대상어 + 제목·요약에 교통 관련어
조건A = 목록['제목'].fillna('').str.contains('고령|노인|어르신|면허')
조건B = (목록['제목'].fillna('') + ' ' + 목록['요약'].fillna('')).str.contains('운전|교통|보행|이동|버스|면허')
대상 = 목록[조건A & 조건B].copy().reset_index(drop=True)
print('1차 필터 후:', len(대상))


def pdf글자(내용):
    with pymupdf.open(stream=내용, filetype='pdf') as 문서:
        return '\n'.join(쪽.get_text() for 쪽 in 문서)


def hwpx글자(내용):
    글 = []
    with zipfile.ZipFile(io.BytesIO(내용)) as z:
        for 이름 in sorted(n for n in z.namelist() if re.match(r'Contents/section\d+\.xml', n)):
            xml = z.read(이름).decode('utf-8', errors='ignore')
            글 += re.findall(r'<hp:t>([^<]*)</hp:t>', xml)
    return '\n'.join(글)


def 본문가져오기(행):
    응답 = requests.get(행['링크'], headers=헤더, timeout=30)
    응답.raise_for_status()
    s = BeautifulSoup(응답.text, 'html.parser')
    if 행['종류'] == '정책뉴스':
        v = s.select_one('div.view_cont')
        return (v.get_text('\n', strip=True) if v else ''), '본문'
    첨부 = []
    for a in s.select('a'):
        이름 = a.get_text(' ', strip=True)
        주소 = a.get('href') or ''
        if '/common/download.do' in 주소 and re.search(r'\.(pdf|hwpx)$', 이름, re.I):
            첨부.append((이름, 'https://www.korea.kr' + 주소))
    첨부.sort(key=lambda x: 0 if x[0].lower().endswith('.pdf') else 1)      # PDF 우선
    for 이름, 주소 in 첨부:
        time.sleep(1)
        파일 = requests.get(주소, headers=헤더, timeout=60)
        if 파일.status_code != 200 or len(파일.content) < 100:
            continue
        try:
            if 이름.lower().endswith('.pdf') and 파일.content[:4] == b'%PDF':
                return pdf글자(파일.content), 'PDF'
            if 이름.lower().endswith('.hwpx') and 파일.content[:2] == b'PK':
                return hwpx글자(파일.content), 'HWPX'
        except Exception as e:
            print('   첨부 읽기 실패:', 이름, e)
    v = s.select_one('div.view_cont')                                      # 첨부가 없으면 화면 본문이라도
    return (v.get_text('\n', strip=True) if v else ''), '화면'


본문, 출처 = [], []
for i, 행 in 대상.iterrows():
    try:
        글, 종류 = 본문가져오기(행)
    except Exception as e:
        글, 종류 = '', f'오류: {e}'
    본문.append(re.sub(r'\s+', ' ', 글).strip())
    출처.append(종류)
    print(f'{i + 1}/{len(대상)} {행["날짜"]} {종류} {len(본문[-1]):,}자  {행["제목"][:30]}')
    time.sleep(1)

대상['본문'] = 본문
대상['본문출처'] = 출처
대상.to_csv(f'{출력}/정책브리핑_본문_2015_2025.csv', index=False, encoding='utf-8-sig')
print('\n본문 출처:', 대상['본문출처'].value_counts().to_dict())
print('본문 비어 있음:', (대상['본문'].str.len() < 50).sum(), '건')
