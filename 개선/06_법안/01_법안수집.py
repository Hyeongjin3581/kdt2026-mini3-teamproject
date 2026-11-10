# [개인 보완] 회고 ① 크롤링 확장 — C안: 열린국회정보 Open API로 고령운전자 관련 법률안 수집
# 실행: 저장소 최상위에서 python "개선/06_법안/01_법안수집.py"
#
# 출처: 열린국회정보 (open.assembly.go.kr) — 의안정보시스템(likms)은 robots.txt 로 일반 수집을 막고 있어 공식 API를 쓴다
#   - 국회의원 발의법률안: /portal/openapi/nzmimeepazxkubdpn (AGE 필수, BILL_NAME 검색)
#   - 법률안 제안이유 및 주요내용: /portal/openapi/BPMBILLSUMMARY (BILL_NO 필수)
#   - 인증키는 개선/06_법안/key.txt 에 두고 git 에 올리지 않는다 (.gitignore)
#
# 고령운전자 법안은 제목이 대부분 '도로교통법 일부개정법률안'이라 제목으로는 못 고른다.
# 그래서 20~22대(2016~현재) 도로교통법·교통안전법 개정안을 모두 받고, 제안이유(주요내용)를 읽어 고른다.

import time
import requests
import pandas as pd

출력 = '개선/06_법안'
KEY = open(f'{출력}/key.txt', encoding='utf-8').read().strip()
기본 = 'https://open.assembly.go.kr/portal/openapi/'


def 받기(서비스, 인자, 시도=4):
    for n in range(시도):
        try:
            r = requests.get(기본 + 서비스, params={'KEY': KEY, 'Type': 'json', **인자}, timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            if n == 시도 - 1:
                raise
            print(f'   연결 오류 → {5 * 2 ** n}초 후 재시도 ({e.__class__.__name__})')
            time.sleep(5 * 2 ** n)


def 행만(j, 서비스):
    if 서비스 not in j:
        return [], 0
    머리, *몸 = j[서비스]
    전체 = 머리['head'][0]['list_total_count']
    return (몸[0]['row'] if 몸 else []), 전체


# 1) 법안 목록
목록 = []
for 대수 in ['20', '21', '22']:
    for 법 in ['도로교통법', '교통안전법']:
        쪽 = 1
        while True:
            행, 전체 = 행만(받기('nzmimeepazxkubdpn', {'AGE': 대수, 'BILL_NAME': 법, 'pIndex': 쪽, 'pSize': 100}), 'nzmimeepazxkubdpn')
            목록 += 행
            print(f'{대수}대 {법} {쪽}쪽: {len(행)}건 / 전체 {전체}')
            if not 행 or 쪽 * 100 >= 전체:
                break
            쪽 += 1
            time.sleep(0.5)
목록 = pd.DataFrame(목록).drop_duplicates('BILL_NO')
목록 = 목록[목록['BILL_NAME'].str.contains('도로교통법|교통안전법')]      # 'OO법 등' 다른 법 섞임 방지
print('법안 수 (중복 제거):', len(목록))

# 2) 제안이유·주요내용
요약 = []
for i, 번호 in enumerate(목록['BILL_NO']):
    행, _ = 행만(받기('BPMBILLSUMMARY', {'BILL_NO': 번호, 'pIndex': 1, 'pSize': 5}), 'BPMBILLSUMMARY')
    요약.append(행[0].get('SUMMARY', '') if 행 else '')
    if (i + 1) % 100 == 0:
        print(f'제안이유 {i + 1}/{len(목록)}')
    time.sleep(0.3)
목록['SUMMARY'] = 요약
보관열 = ['AGE', 'BILL_NO', 'BILL_ID', 'BILL_NAME', 'PROPOSER', 'PROPOSE_DT', 'COMMITTEE', 'PROC_RESULT', 'PROC_DT', 'SUMMARY']
목록[[c for c in 보관열 if c in 목록.columns]].to_csv(f'{출력}/법안_원자료.csv', index=False, encoding='utf-8-sig')
print('저장:', f'{출력}/법안_원자료.csv', len(목록), '/ 제안이유 없음:', sum(1 for s in 요약 if not s))
