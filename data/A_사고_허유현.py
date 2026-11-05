# MINI3 - A 담당: 고령운전자 교통사고 분석 (2022~2024)
# 실행 위치: MINI3 폴더
# 설치: pip install pandas requests matplotlib seaborn

import os
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 그래프 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 1] 파일 위치 설정
코드표파일 = './data/data/raw/사고API_시군구코드표_2022_2024.csv'
키파일 = './data/key.txt'
중간파일 = './data/data/raw/수집_A_중간저장.csv'
실패파일 = './data/data/raw/수집_A_실패목록.csv'
결과파일 = './data/data/clean/정제_A_사고.csv'
인구파일 = './data/data/clean/정제_B_반납인구.csv'
그래프폴더 = './data/graphs'
os.makedirs('./data/data/clean', exist_ok=True)
os.makedirs(그래프폴더, exist_ok=True)

# 2] 자료 수집 준비
코드표 = pd.read_csv(코드표파일, dtype={'siDo': str, 'guGun': str})
print('[3-3] 코드표:', len(코드표), '행 / 기대: 688행')
if len(코드표) != 688:
    print('주의: 코드표 행 수가 가이드와 다릅니다. 코드를 확인하세요.')

with open(키파일, 'r', encoding='utf-8') as f:
    서비스키 = f.read().strip()

주소 = 'https://apis.data.go.kr/B552061/lgStat/getRestLgStat'

# 3-5] 강남구 API 테스트
테스트파라미터 = {'serviceKey': 서비스키, 'searchYearCd': '2024',
             'siDo': '1100', 'guGun': '1116', 'type': 'json',
             'numOfRows': '13', 'pageNo': '1'}
테스트응답 = requests.get(주소, params=테스트파라미터, timeout=30)
테스트응답.raise_for_status()
테스트자료 = 테스트응답.json()
테스트항목 = 테스트자료.get('items', {}).get('item', [])
if isinstance(테스트항목, dict):
    테스트항목 = [테스트항목]
테스트전체 = [x for x in 테스트항목 if x.get('acc_cl_nm') == '전체사고']
테스트고령 = [x for x in 테스트항목 if x.get('acc_cl_nm') == '고령운전자사고']
if len(테스트전체) != 1 or len(테스트고령) != 1:
    raise ValueError('강남구 API 테스트 실패: 응답 형식 또는 사고 유형을 확인하세요. ' + str(테스트자료)[:400])
print('[3-5] 강남구 테스트:', '전체', 테스트전체[0]['acc_cnt'],
      '/ 고령', 테스트고령[0]['acc_cnt'])

# 3-6] 시군구별 API 반복 수집 (이미 저장한 데이터는 다시 요청하지 않음)
if os.path.exists(중간파일):
    수집자료 = pd.read_csv(중간파일, dtype={'siDo': str, 'guGun': str})
    print('이전 수집자료', len(수집자료), '행 불러옴')

    # 예전 수집 파일은 API 원본 형식이어서 '연도', 'siDo', 'guGun'이 없음
    # 코드표의 연도와 시군구명을 이용해 필요한 열을 연결한다.
    if '연도' not in 수집자료.columns and 'std_year' in 수집자료.columns:
        수집자료 = 수집자료.rename(columns={'std_year': '연도'})

    if 'siDo' not in 수집자료.columns or 'guGun' not in 수집자료.columns:
        필요한코드표 = 코드표[['연도', 'siDo', 'guGun', '시군구명']].copy()
        수집자료['연도'] = pd.to_numeric(수집자료['연도'], errors='coerce')
        필요한코드표['연도'] = pd.to_numeric(필요한코드표['연도'], errors='coerce')
        # 한 연도에 같은 시군구명이 중복되어 있으면 코드가 모호하므로 중단
        if 필요한코드표.duplicated(['연도', '시군구명']).any():
            raise ValueError('코드표에 같은 연도·시군구명이 중복되어 있습니다. 기존 수집파일은 변경하지 않았습니다.')
        수집자료 = pd.merge(
            수집자료, 필요한코드표,
            left_on=['연도', 'sido_sgg_nm'], right_on=['연도', '시군구명'],
            how='left'
        )
        if 수집자료[['siDo', 'guGun']].isnull().any().any():
            미연결 = 수집자료[수집자료['siDo'].isnull()][['연도', 'sido_sgg_nm']].drop_duplicates()
            print('코드표에서 찾지 못한 지역:')
            print(미연결.head(20))
            raise ValueError('기존 CSV와 코드표의 지역명이 달라 자동 연결을 중단했습니다. 원본 파일은 그대로입니다.')
        수집자료 = 수집자료.drop(columns=['시군구명'])
        수집자료['siDo'] = 수집자료['siDo'].astype(str)
        수집자료['guGun'] = 수집자료['guGun'].astype(str)
        print('기존 API 원본 열을 코드표와 연결했습니다.')
else:
    수집자료 = pd.DataFrame()

# 코드표의 요청 단위와 수집자료의 사고 유형이 정확히 대응하는지 먼저 확인
if len(수집자료) > 0:
    요청확인 = 수집자료.groupby(['연도', 'siDo', 'guGun'])['acc_cl_nm'].agg(['count', 'nunique'])
    if (요청확인['count'] > 2).any():
        raise ValueError('기존 CSV에 동일 요청의 중복 사고 유형이 있습니다. 원본을 보존하고 중단합니다.')

실패목록 = []
성공요청 = 0
for i in range(len(코드표)):
    행 = 코드표.iloc[i]
    연도 = str(행['연도'])
    시도코드 = str(행['siDo'])
    시군구코드 = str(행['guGun'])

    # 한 번 성공한 시군구/연도는 건너뛰기 (두 사고 유형이 모두 있어야 함)
    if len(수집자료) > 0:
        기존 = 수집자료[(수집자료['연도'].astype(str) == 연도) &
                      (수집자료['siDo'].astype(str) == 시도코드) &
                      (수집자료['guGun'].astype(str) == 시군구코드)]
        if ('전체사고' in 기존['acc_cl_nm'].values and
                '고령운전자사고' in 기존['acc_cl_nm'].values):
            continue

    파라미터 = {'serviceKey': 서비스키, 'searchYearCd': 연도,
            'siDo': 시도코드, 'guGun': 시군구코드,
            'type': 'json', 'numOfRows': '13', 'pageNo': '1'}
    try:
        응답 = requests.get(주소, params=파라미터, timeout=30)
        응답.raise_for_status()
        내용 = 응답.json()
        항목들 = 내용.get('items', {}).get('item', [])
        if isinstance(항목들, dict):
            항목들 = [항목들]
        선택항목 = [x for x in 항목들 if x.get('acc_cl_nm') in ['전체사고', '고령운전자사고']]
        if len(선택항목) != 2:
            실패목록.append({'연도': 연도, 'siDo': 시도코드, 'guGun': 시군구코드,
                          '사유': str(내용)[:300]})
            continue
        새자료 = []
        for 항목 in 선택항목:
            새자료.append({'연도': 연도, 'siDo': 시도코드, 'guGun': 시군구코드,
                        'sido_sgg_nm': 항목.get('sido_sgg_nm'),
                        'acc_cl_nm': 항목.get('acc_cl_nm'),
                        'acc_cnt': 항목.get('acc_cnt'),
                        'dth_dnv_cnt': 항목.get('dth_dnv_cnt'),
                        'ftlt_rate': 항목.get('ftlt_rate')})
        수집자료 = pd.concat([수집자료, pd.DataFrame(새자료)], ignore_index=True)
        성공요청 += 1
    except (requests.RequestException, ValueError) as 오류:
        실패목록.append({'연도': 연도, 'siDo': 시도코드, 'guGun': 시군구코드,
                      '사유': str(오류)[:300]})

    # 20회마다 중간 저장: 도중에 종료되어도 재시작 가능
    if (i + 1) % 20 == 0:
        수집자료.to_csv(중간파일, index=False, encoding='utf-8-sig')
        print('[3-6]', i + 1, '/', len(코드표), '확인 / 이번 실행 성공', 성공요청)
    time.sleep(0.2)

수집자료.to_csv(중간파일, index=False, encoding='utf-8-sig')
pd.DataFrame(실패목록, columns=['연도', 'siDo', 'guGun', '사유']).to_csv(
    실패파일, index=False, encoding='utf-8-sig')
print('[3-6] 수집 완료 / 원자료 행:', len(수집자료), '/ 이번 실행 실패:', len(실패목록))

# 4-1] 숫자형 변환 및 결측치 확인
for 열 in ['연도', 'acc_cnt', 'dth_dnv_cnt', 'ftlt_rate']:
    수집자료[열] = pd.to_numeric(수집자료[열], errors='coerce')
print('[4-1] 결측치 확인')
print(수집자료[['연도', 'sido_sgg_nm', 'acc_cnt', 'dth_dnv_cnt']].isnull().sum())

# 4-2] 시도명 추출 및 명칭 통일
수집자료['시도명'] = 수집자료['sido_sgg_nm'].str.split(' ').str[0]
수집자료['시도명'] = 수집자료['시도명'].replace({
    '강원도': '강원특별자치도', '전라북도': '전북특별자치도',
    '제주도': '제주특별자치도'})

# 4-3] 시도별, 연도별, 사고 유형별 집계
집계 = 수집자료.groupby(['연도', '시도명', 'acc_cl_nm']).agg(
    사고건수=('acc_cnt', 'sum'), 사망자수=('dth_dnv_cnt', 'sum')).reset_index()
전체 = 집계[집계['acc_cl_nm'] == '전체사고'].copy()
고령 = 집계[집계['acc_cl_nm'] == '고령운전자사고'].copy()
전체 = 전체.rename(columns={'사고건수': '전체사고건수', '사망자수': '전체사망자수'})
고령 = 고령.rename(columns={'사고건수': '고령사고건수', '사망자수': '고령사망자수'})
결과 = pd.merge(고령[['연도', '시도명', '고령사고건수', '고령사망자수']],
             전체[['연도', '시도명', '전체사고건수', '전체사망자수']],
             on=['연도', '시도명'], how='outer')

# 4-4] 사고 100건당 사망자 수(%) 계산: 시군구별 비율을 평균 내면 안 됨
결과['고령치사율'] = 결과['고령사망자수'] / 결과['고령사고건수'] * 100
결과['전체치사율'] = 결과['전체사망자수'] / 결과['전체사고건수'] * 100

# 4-5] B 담당의 65세 이상 인구 자료 병합
결과['고령사고_만명당'] = float('nan')
인구병합성공 = False
if os.path.exists(인구파일):
    인구 = pd.read_csv(인구파일)
    필요열 = ['연도', '시도명', '65세이상인구']
    if all(열 in 인구.columns for 열 in 필요열):
        인구['연도'] = pd.to_numeric(인구['연도'], errors='coerce')
        인구['65세이상인구'] = pd.to_numeric(인구['65세이상인구'], errors='coerce')
        인구['시도명'] = 인구['시도명'].replace({
            '강원도': '강원특별자치도', '전라북도': '전북특별자치도',
            '제주도': '제주특별자치도'})
        인구 = 인구[필요열].drop_duplicates()
        if 인구.duplicated(['연도', '시도명']).sum() == 0:
            결과 = 결과.drop(columns=['고령사고_만명당'])
            결과 = pd.merge(결과, 인구, on=['연도', '시도명'], how='left')
            결과['고령사고_만명당'] = 결과['고령사고건수'] / 결과['65세이상인구'] * 10000
            인구병합성공 = True
            print('[4-5] 인구 병합 후 결측치:', 결과['65세이상인구'].isnull().sum())
        else:
            print('[4-5] 인구 파일에 같은 연도·시도가 중복되어 있어 H1 분석 보류')
    else:
        print('[4-5] B 파일에 필요한 열이 없습니다:', 필요열)
else:
    print('[4-5] B 인구 파일이 없어 H1 분석은 보류합니다.')

결과 = 결과.sort_values(['연도', '시도명']).reset_index(drop=True)
결과.to_csv(결과파일, index=False, encoding='utf-8-sig')
print('[4-6] 정제 자료 저장:', 결과파일, '/ 행 수:', len(결과))

# 5-1] 공식 연도별 전국 통계와 비교
공식 = pd.DataFrame({
    '연도': [2022, 2023, 2024],
    '전체사고건수_공식': [196836, 198296, 196349],
    '고령사고건수_공식': [34652, 39614, 42369],
    '전체사망자수_공식': [2735, 2551, 2521],
    '고령사망자수_공식': [735, 745, 761]})
전국 = 결과.groupby('연도')[['전체사고건수', '고령사고건수',
                           '전체사망자수', '고령사망자수']].sum().reset_index()
검증 = pd.merge(전국, 공식, on='연도', how='outer')
for 열 in ['전체사고건수', '고령사고건수', '전체사망자수', '고령사망자수']:
    검증[열 + '_차이'] = 검증[열] - 검증[열 + '_공식']
print('[5-1] 공식 통계 비교 (차이가 0이어야 일치)')
print(검증[['연도', '전체사고건수_차이', '고령사고건수_차이',
          '전체사망자수_차이', '고령사망자수_차이']])

# 검증 조건: 요청 688개 모두 성공, 51개 지역·연도 조합, 숫자 결측 없음, 공식 총계 일치
요청수 = 수집자료.groupby(['연도', 'siDo', 'guGun'])['acc_cl_nm'].nunique()
완료요청수 = (요청수 == 2).sum()
숫자결측 = 수집자료[['연도', 'acc_cnt', 'dth_dnv_cnt', '시도명']].isnull().sum().sum()
차이열 = ['전체사고건수_차이', '고령사고건수_차이',
        '전체사망자수_차이', '고령사망자수_차이']
검증완료 = (완료요청수 == len(코드표) and len(결과) == 51 and
         숫자결측 == 0 and len(검증) == 3 and
         (검증[차이열] == 0).all().all())
print('[5-1] 완료 요청:', 완료요청수, '/', len(코드표))
print('[5-1] 전국 통계 검증 통과:', 검증완료)
if not 검증완료:
    print('주의: 수집 누락 또는 통계 불일치가 있습니다. 가설 결과를 확정하지 마세요.')

# 5-2] H1: 65세 이상 인구 1만 명당 고령운전자 사고의 지역 간 최대/최소 차이
if 인구병합성공 and 검증완료 and 결과['고령사고_만명당'].notnull().all() and (결과['고령사고_만명당'] > 0).all():
    print('[5-2] H1 연도별 최대/최소 비율')
    for 연도 in [2022, 2023, 2024]:
        해당연도 = 결과[결과['연도'] == 연도]
        비율 = 해당연도['고령사고_만명당'].max() / 해당연도['고령사고_만명당'].min()
        print(연도, '최대/최소:', round(비율, 2), '배 / 2배 이상:', 비율 >= 2)

    plt.figure(figsize=(12, 8))
    sns.barplot(data=결과, x='고령사고_만명당', y='시도명', hue='연도')
    plt.title('시도별 65세 이상 인구 1만 명당 고령운전자 사고')
    plt.xlabel('사고 건수 (인구 1만 명당)')
    plt.ylabel('시도')
    plt.tight_layout()
    plt.savefig(그래프폴더 + '/A_H1_시도별_만명당_사고.png', dpi=150)
    plt.show()
else:
    print('[5-2] H1 보류: 인구 자료 또는 수집 검증이 완료되지 않았습니다.')

# 5-3] H2: 모든 17개 시도 × 3개 연도에서 고령 치사율 > 전체 치사율인지
결과['H2_조건충족'] = 결과['고령치사율'] > 결과['전체치사율']
print('[5-3] H2 조건 충족:', 결과['H2_조건충족'].sum(), '/', len(결과))
print('[5-3] 조건 미충족 지역')
print(결과[결과['H2_조건충족'] == False][['연도', '시도명', '고령치사율', '전체치사율']])
if 검증완료:
    print('[5-3] H2 전체 충족:', 결과['H2_조건충족'].all())
else:
    print('[5-3] H2 최종 판단 보류: 수집 검증이 완료되지 않았습니다.')

# 5-4] 2024년 시도별 치사율 비교 그래프
자료2024 = 결과[결과['연도'] == 2024]
비교그래프 = 자료2024[['시도명', '고령치사율', '전체치사율']].set_index('시도명')
비교그래프.plot(kind='bar', figsize=(13, 6))
plt.title('2024년 시도별 고령운전자 사고 치사율과 전체 사고 치사율')
plt.ylabel('사고 100건당 사망자 수 (%)')
plt.xlabel('시도')
plt.xticks(rotation=60)
plt.tight_layout()
plt.savefig(그래프폴더 + '/A_H2_2024_시도별_치사율.png', dpi=150)
plt.show()

# 5-5] 전국 연도별 치사율 변화 (사망자 합계 / 사고 합계)
전국['고령치사율'] = 전국['고령사망자수'] / 전국['고령사고건수'] * 100
전국['전체치사율'] = 전국['전체사망자수'] / 전국['전체사고건수'] * 100
plt.figure(figsize=(8, 5))
plt.plot(전국['연도'], 전국['고령치사율'], marker='o', label='고령운전자 사고')
plt.plot(전국['연도'], 전국['전체치사율'], marker='o', label='전체 사고')
plt.xticks([2022, 2023, 2024])
plt.title('2022~2024년 전국 교통사고 치사율 변화')
plt.xlabel('연도')
plt.ylabel('사고 100건당 사망자 수 (%)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(그래프폴더 + '/A_전국_연도별_치사율.png', dpi=150)
plt.show()

# 6] 결과 파일을 마지막에 다시 저장 (H2 조건 충족 열 포함)
결과.to_csv(결과파일, index=False, encoding='utf-8-sig')
print('[6] 최종 파일:', 결과파일)
