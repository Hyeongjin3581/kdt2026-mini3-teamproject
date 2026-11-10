# [개인 보완] 회고 ① 크롤링 확장 — B안: 국가법령정보 Open API로 고령운전자 면허 반납 지원 조례 수집
# 실행: 저장소 최상위에서 python "개선/05_조례/01_조례수집.py"
#
# 출처: 법제처 국가법령정보 공동활용 Open API (open.law.go.kr), 현행 자치법규
#   - 목록: https://www.law.go.kr/DRF/lawSearch.do?target=ordin&type=JSON
#   - 본문: https://www.law.go.kr/DRF/lawService.do?target=ordin&type=JSON&MST=자치법규일련번호
#   - 인증값(OC)은 개선/05_조례/oc.txt 에 두고 git 에 올리지 않는다 (.gitignore)
#
# 검색 전략 (제목만 찾으면 '노인 교통안전 조례' 안에 반납 지원 조항이 있는 경우를 놓친다)
#   ① 제목 검색: '고령운전자'
#   ② 본문 검색: '자진반납', '운전면허 반납'
#   세 결과를 합쳐 자치법규일련번호로 중복을 지운 뒤 본문을 모두 받는다.

import json
import time
import requests
import pandas as pd

출력 = '개선/05_조례'
OC = open(f'{출력}/oc.txt', encoding='utf-8').read().strip()
목록주소 = 'https://www.law.go.kr/DRF/lawSearch.do'
본문주소 = 'https://www.law.go.kr/DRF/lawService.do'
def 받기(주소, 인자, 시도=4):
    """서버가 연결을 끊는 경우가 있어 5·10·20초 쉬고 다시 시도한다."""
    for n in range(시도):
        try:
            r = requests.get(주소, params=인자, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if n == 시도 - 1:
                raise
            print(f'   연결 오류 → {5 * 2 ** n}초 후 재시도 ({e.__class__.__name__})')
            time.sleep(5 * 2 ** n)


검색목록 = [('고령운전자', 1), ('자진반납', 2), ('운전면허 반납', 2)]      # (검색어, 1=제목 2=본문)


def 목록받기(검색어, 범위):
    행, 쪽 = [], 1
    while True:
        r = 받기(목록주소, {'OC': OC, 'target': 'ordin', 'type': 'JSON', 'query': 검색어,
                         'search': 범위, 'display': 100, 'page': 쪽})['OrdinSearch']
        법 = r.get('law') or []
        법 = 법 if isinstance(법, list) else [법]
        행 += 법
        print(f'{검색어} ({"제목" if 범위 == 1 else "본문"}) {쪽}쪽: {len(법)}건 / 전체 {r.get("totalCnt")}')
        if len(행) >= int(r.get('totalCnt', 0)) or not 법:
            return 행
        쪽 += 1
        time.sleep(1)


모음 = []
for 검색어, 범위 in 검색목록:
    for x in 목록받기(검색어, 범위):
        x['검색'] = f'{검색어}({"제목" if 범위 == 1 else "본문"})'
        모음.append(x)
    time.sleep(1)
목록 = pd.DataFrame(모음)
목록 = (목록.groupby('자치법규일련번호', as_index=False)
          .agg({**{c: 'first' for c in 목록.columns if c not in ['자치법규일련번호', '검색']}, '검색': lambda s: ', '.join(sorted(set(s)))}))
print('\n합친 뒤 (중복 제거):', len(목록))

# 본문 받기: 조문·부칙을 글자로 이어 붙이고, 부칙 공포일자 중 가장 이른 날을 최초 제정일로 본다
본문들, 최초 = [], []
for i, 일련번호 in enumerate(목록['자치법규일련번호']):
    try:
        j = 받기(본문주소, {'OC': OC, 'target': 'ordin', 'type': 'JSON', 'MST': 일련번호})['LawService']
        조 = (j.get('조문') or {}).get('조') or []
        조 = 조 if isinstance(조, list) else [조]
        부칙 = j.get('부칙') or {}
        부칙 = 부칙 if isinstance(부칙, list) else [부칙]
        글 = ' '.join(c.get('조내용', '') if isinstance(c.get('조내용'), str) else json.dumps(c.get('조내용'), ensure_ascii=False) for c in 조)
        일자 = sorted(x for b in 부칙 for x in (b.get('부칙공포일자') if isinstance(b.get('부칙공포일자'), list) else [b.get('부칙공포일자')]) if x)
        본문들.append(글)
        최초.append(일자[0] if 일자 else '')
    except Exception as e:
        본문들.append('')
        최초.append('')
        print('  본문 오류', 일련번호, e)
    if (i + 1) % 50 == 0:
        print(f'본문 {i + 1}/{len(목록)}')
    time.sleep(1)
목록['본문'] = 본문들
목록['최초공포일자'] = 최초
목록 = 목록.drop(columns=['자치법규상세링크'], errors='ignore')   # 링크에 인증값(OC)이 들어 있어 저장하지 않음
목록.to_csv(f'{출력}/조례_원자료.csv', index=False, encoding='utf-8-sig')
print('저장:', f'{출력}/조례_원자료.csv', len(목록))
