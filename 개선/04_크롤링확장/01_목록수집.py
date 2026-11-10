# [개인 보완] 회고 ① 크롤링 확장 — A안: 정책브리핑 수집 범위 넓히기 (1) 목록 수집
# 실행: 저장소 최상위에서 python "개선/04_크롤링확장/01_목록수집.py"
#
# 팀 D 코드(Playwright, 2022~2024, 보도자료·정책뉴스, 중립 검색어 6개)를 그대로 따르되 두 가지를 바꾼다.
#   ① 기간: 2022~2024 → 2015~2025 (사례 수를 늘리고 시기별 흐름을 보기 위해)
#   ② 방식: 목록 페이지는 페이지 번호(pageIndex)로 바로 열 수 있어 브라우저 없이 requests 로 받는다.
#      (D 코드 6-4에서 겪은 '검색어 강조 표시 앞뒤 띄어쓰기' 문제는 get_text(strip=True)로 조각을 붙여 피한다)
# 수집 허용: https://www.korea.kr/robots.txt → User-Agent: * / Allow: /  (2026-11-10 확인)
# 예의: 요청 사이 1초 쉬고, 같은 페이지를 다시 받지 않도록 결과를 파일로 남긴다.

import time
import requests
import pandas as pd
from bs4 import BeautifulSoup

출력 = '개선/04_크롤링확장'
검색어목록 = ['고령운전자', '면허 반납', '고령자 교통안전', '어르신 교통', '노인 교통사고', '고령 보행자']   # 팀 D와 동일 (중립 검색어)
게시판목록 = [('보도자료', 'https://www.korea.kr/briefing/pressReleaseList.do'),
           ('정책뉴스', 'https://www.korea.kr/news/policyNewsList.do')]
시작일, 종료일 = '2015-01-01', '2025-12-31'
헤더 = {'User-Agent': 'Mozilla/5.0 (KDT student research project)'}


def 글자(태그):
    """검색어 강조(<span>) 때문에 생기는 띄어쓰기 없이 화면에 보이는 그대로 이어 붙인다."""
    return 태그.get_text('', strip=True) if 태그 else ''


행 = []
for 검색어 in 검색어목록:
    for 종류, 주소 in 게시판목록:
        쪽 = 1
        while True:
            응답 = requests.get(주소, params={'srchWord': 검색어, 'startDate': 시작일, 'endDate': 종료일, 'pageIndex': 쪽},
                              headers=헤더, timeout=30)
            응답.raise_for_status()
            카드들 = BeautifulSoup(응답.text, 'html.parser').select('div.article_body div.list_type li a')
            if not 카드들:
                break
            for 카드 in 카드들:
                출처 = 카드.select('span.source span')
                링크 = 카드.get('href') or ''
                행.append({'검색어': 검색어, '종류': 종류, '제목': 글자(카드.select_one('strong')),
                          '요약': 글자(카드.select_one('span.lead')),
                          '날짜': 출처[0].get_text(strip=True) if len(출처) > 0 else '',
                          '부처': 출처[1].get_text(strip=True) if len(출처) > 1 else '',
                          '링크': 'https://www.korea.kr' + 링크.split('&')[0] if 링크 else ''})
            print(f'{검색어} / {종류} / {쪽}쪽: {len(카드들)}건')
            쪽 += 1
            time.sleep(1)
        time.sleep(1)

목록 = pd.DataFrame(행)
목록.to_csv(f'{출력}/정책브리핑_수집_2015_2025.csv', index=False, encoding='utf-8-sig')
print('\n수집 건수:', len(목록))
print('링크 기준 중복 제거:', 목록['링크'].nunique())
print(목록.groupby(['종류'])['링크'].nunique().to_string())
