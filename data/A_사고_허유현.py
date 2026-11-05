# -*- coding: utf-8 -*-
"""팀원 A: 2022~2024 고령운전자 교통사고 분석.
실행 전: pip install httpx pandas numpy matplotlib seaborn
같은 폴더에 key.txt, data/raw/사고API_시군구코드표_2022_2024.csv 준비.
선택: data/clean/정제_B_반납인구.csv (연도, 시도명, 65세이상인구)
"""
from pathlib import Path
import time
import httpx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

BASE = Path(__file__).resolve().parent
RAW = BASE / 'data' / 'raw'
CLEAN = BASE / 'data' / 'clean'
GRAPHS = BASE / 'graphs'
for folder in (RAW, CLEAN, GRAPHS):
    folder.mkdir(parents=True, exist_ok=True)

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

URL = 'https://apis.data.go.kr/B552061/lgStat/getRestLgStat'
CODE_FILE = RAW / '사고API_시군구코드표_2022_2024.csv'
COLLECTED_FILE = RAW / '수집_A_사고_2022_2024.csv'
B_FILE = CLEAN / '정제_B_반납인구.csv'
KEEP_TYPES = ['전체사고', '고령운전자사고']
RENAME_REGION = {'강원도': '강원특별자치도', '전라북도': '전북특별자치도', '제주도': '제주특별자치도'}

# 3-5: 인증키 확인 및 한 건 테스트
key_path = BASE / 'key.txt'
if not key_path.exists():
    raise FileNotFoundError(f'{key_path} 파일을 만들고 디코딩 인증키를 저장하세요.')
service_key = key_path.read_text(encoding='utf-8').strip()
if not service_key:
    raise ValueError('key.txt가 비어 있습니다.')


def fetch_items(client, year, sido, gugun):
    params = {'serviceKey': service_key, 'searchYearCd': str(year),
              'siDo': str(sido), 'guGun': str(gugun),
              'type': 'json', 'numOfRows': 100, 'pageNo': 1}
    response = client.get(URL, params=params)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError as e:
        raise ValueError(f'JSON 응답이 아닙니다: {response.text[:250]}') from e
    if str(payload.get('resultCode')) != '00':
        raise ValueError(f"API 오류: {payload.get('resultCode')} / {payload.get('resultMsg')}")
    total = int(payload.get('totalCount', 0))
    if total > 100:
        raise ValueError(f'페이지 추가 수집 필요: totalCount={total}')
    items = payload.get('items', {}).get('item', [])
    if isinstance(items, dict):
        items = [items]
    if len(items) != total:
        raise ValueError(f'응답 항목 수 불일치: {len(items)} / {total}')
    return items


with httpx.Client(timeout=30.0) as client:
    test_items = fetch_items(client, 2024, 1100, 1116)
print('\n[3-5] 강남구 API 테스트 성공')
test_df = pd.DataFrame(test_items)
print(test_df.loc[test_df['acc_cl_nm'].isin(KEEP_TYPES),
                  ['std_year', 'sido_sgg_nm', 'acc_cl_nm', 'acc_cnt', 'dth_dnv_cnt']].to_string(index=False))

# 3-6: 시군구 코드표로 전체 수집 (기존 수집 파일이 있으면 재사용)
if COLLECTED_FILE.exists():
    print(f'\n[3-6] 기존 수집 파일 재사용: {COLLECTED_FILE}')
    df = pd.read_csv(COLLECTED_FILE, encoding='utf-8-sig')
elif CODE_FILE.exists():
    codes = pd.read_csv(CODE_FILE, encoding='utf-8-sig', dtype={'siDo': str, 'guGun': str})
    required = {'연도', 'siDo', 'guGun'}
    if not required.issubset(codes.columns):
        raise ValueError(f'코드표 컬럼 확인 필요: {list(codes.columns)} / 필요한 컬럼: {required}')
    if codes[['연도', 'siDo', 'guGun']].isnull().any().any():
        raise ValueError('코드표에 연도 또는 지역 코드 결측치가 있습니다.')
    if codes.duplicated(['연도', 'siDo', 'guGun']).any():
        raise ValueError('코드표에 중복된 연도-시도-시군구 코드가 있습니다.')
    print(f'\n[3-6] 총 {len(codes)}건 호출 시작 (예상 688건)')
    records = []
    failures = []
    with httpx.Client(timeout=30.0) as client:
        for i, row in enumerate(codes.itertuples(index=False), 1):
            r = row._asdict()
            year, sido, gugun = r['연도'], r['siDo'], r['guGun']
            try:
                items = fetch_items(client, year, sido, gugun)
                chosen = [item for item in items if item.get('acc_cl_nm') in KEEP_TYPES]
                if len(chosen) != 2:
                    raise ValueError(f'사고 유형 2개가 아닙니다: {[x.get("acc_cl_nm") for x in chosen]}')
                records.extend(chosen)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as e:
                failures.append({'연도': year, 'siDo': sido, 'guGun': gugun, '오류': str(e)})
                print(f'실패 {i}/{len(codes)}: {year}/{sido}/{gugun}: {e}')
            if i % 50 == 0:
                print(f'{i}/{len(codes)}건 완료, 성공 행 {len(records)}, 실패 {len(failures)}')
                pd.DataFrame(records).to_csv(RAW / '수집_A_중간저장.csv', index=False, encoding='utf-8-sig')
            time.sleep(0.2)
    if failures:
        pd.DataFrame(failures).to_csv(RAW / '수집_A_실패목록.csv', index=False, encoding='utf-8-sig')
        pd.DataFrame(records).to_csv(RAW / '수집_A_중간저장.csv', index=False, encoding='utf-8-sig')
        raise RuntimeError(f'{len(failures)}건 수집 실패. data/raw/수집_A_실패목록.csv 확인 후 재실행하세요. 완성 파일은 저장하지 않았습니다.')
    df = pd.DataFrame(records)
    df.to_csv(COLLECTED_FILE, index=False, encoding='utf-8-sig')
    print(f'원본 저장: {COLLECTED_FILE} / {len(df)}행')
else:
    print('\n[안내] 688행 코드표가 없어 강남구 테스트만 완료했습니다.')
    print(f'팀원에게 코드표를 받아 이 경로에 넣으세요: {CODE_FILE}')
    print('코드표가 없으면 전체 수집과 시도별 분석은 수행할 수 없습니다.')
    raise SystemExit(0)

# 4-1 ~ 4-4: 전처리
print('\n[4] 수집 데이터 구조')
print(df.info())
required_raw = {'std_year', 'sido_sgg_nm', 'acc_cl_nm', 'acc_cnt', 'dth_dnv_cnt'}
if not required_raw.issubset(df.columns):
    raise ValueError(f'원본 컬럼 부족: {required_raw - set(df.columns)}')
df = df[df['acc_cl_nm'].isin(KEEP_TYPES)].copy()
for col in ['std_year', 'acc_cnt', 'dth_dnv_cnt']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
print('\n결측치 확인:')
print(df[['std_year', 'sido_sgg_nm', 'acc_cl_nm', 'acc_cnt', 'dth_dnv_cnt']].isna().sum())
if df[['std_year', 'sido_sgg_nm', 'acc_cl_nm', 'acc_cnt', 'dth_dnv_cnt']].isna().any().any():
    df[df[['std_year', 'sido_sgg_nm', 'acc_cl_nm', 'acc_cnt', 'dth_dnv_cnt']].isna().any(axis=1)].to_csv(
        CLEAN / 'A_결측치_확인필요.csv', index=False, encoding='utf-8-sig')
    raise ValueError('필수 값 결측치 발견. A_결측치_확인필요.csv를 확인하세요. 0으로 채우지 않습니다.')
df['시도명'] = df['sido_sgg_nm'].str.split().str[0].replace(RENAME_REGION)
if df['시도명'].isna().any():
    raise ValueError('시도명 추출 실패')

# 중복 수집 감지: 동일 연도/시군구/사고 유형이 2번 들어오면 이중 집계됨
if df.duplicated(['std_year', 'sido_sgg_nm', 'acc_cl_nm']).any():
    print('주의: 동일 지역명·연도·사고유형 중복 발견. 군위군 등 행정구역 이력을 확인하세요.')
    print(df[df.duplicated(['std_year', 'sido_sgg_nm', 'acc_cl_nm'], keep=False)][['std_year', 'sido_sgg_nm', 'acc_cl_nm']])

# 4-5: 시도별 합산
agg = df.groupby(['std_year', '시도명', 'acc_cl_nm'], as_index=False).agg(
    사고건수=('acc_cnt', 'sum'), 사망자수=('dth_dnv_cnt', 'sum'))

# 4-6: 전체/고령 부문 합치기
all_df = agg[agg['acc_cl_nm'] == '전체사고'][['std_year', '시도명', '사고건수', '사망자수']].rename(
    columns={'사고건수': '전체사고건수', '사망자수': '전체사망자수'})
old_df = agg[agg['acc_cl_nm'] == '고령운전자사고'][['std_year', '시도명', '사고건수', '사망자수']].rename(
    columns={'사고건수': '고령사고건수', '사망자수': '고령사망자수'})
result = pd.merge(all_df, old_df, on=['std_year', '시도명'], how='outer', indicator=True, validate='one_to_one')
if (result['_merge'] != 'both').any():
    print(result[result['_merge'] != 'both'])
    raise ValueError('전체사고/고령사고의 지역-연도 집계가 일치하지 않습니다.')
result = result.drop(columns='_merge').rename(columns={'std_year': '연도'})
print('\n시도별 집계 행 수:', len(result), '(정상 기대: 51행)')
print(result.groupby('연도')['시도명'].nunique())
if len(result) != 51 or (result.groupby('연도')['시도명'].nunique() != 17).any():
    raise ValueError('17개 시도 × 3년 = 51행이 아닙니다. 수집 코드표를 확인하세요.')

# 4-7: 치사율 재계산
for accident_col, death_col, rate_col in [
    ('고령사고건수', '고령사망자수', '고령치사율'),
    ('전체사고건수', '전체사망자수', '전체치사율')]:
    result[rate_col] = np.where(result[accident_col] > 0,
                                result[death_col] / result[accident_col] * 100, np.nan)

# 6-1: 공식 전국 합계 비교 (전국 값이 다르면 코드표/수집 누락을 확인)
expected = pd.DataFrame({
    '연도': [2022, 2023, 2024],
    '전체사고건수': [196836, 198296, 196349],
    '고령사고건수': [34652, 39614, 42369],
    '전체사망자수': [2735, 2551, 2521],
    '고령사망자수': [735, 745, 761]
})
actual = result.groupby('연도', as_index=False)[['전체사고건수', '고령사고건수', '전체사망자수', '고령사망자수']].sum()
check = actual.merge(expected, on='연도', suffixes=('_실제', '_공식'), validate='one_to_one')
for name in ['전체사고건수', '고령사고건수', '전체사망자수', '고령사망자수']:
    check[name + '_일치'] = check[name + '_실제'] == check[name + '_공식']
check.to_csv(CLEAN / 'A_전국합계_검증.csv', index=False, encoding='utf-8-sig')
print('\n[6-1] 전국 합계 검증:')
print(check.to_string(index=False))
if not check.filter(like='_일치').all().all():
    print('경고: 공식 전국 합계와 차이가 있습니다. 코드표·군위군·누락 지역 확인 후 결과를 사용하세요.')

# 가설 2: 51개 시도-연도 조합 전체 비교
result['고령치사율_더높음'] = result['고령치사율'] > result['전체치사율']
print('\n[가설 2] 연도별 고령치사율 > 전체치사율 지역 수:')
print(result.groupby('연도')['고령치사율_더높음'].agg(['sum', 'count']))
print('가설 2 충족 여부:', bool(result['고령치사율_더높음'].all()))

# 4-8: B팀 고령 인구 파일이 있으면 병합
has_population = False
if B_FILE.exists():
    b = pd.read_csv(B_FILE, encoding='utf-8-sig')
    required_b = {'연도', '시도명', '65세이상인구'}
    if not required_b.issubset(b.columns):
        print(f'B팀 파일의 열 이름을 확인하세요: {list(b.columns)}. 인구 병합을 건너뜁니다.')
    else:
        b['연도'] = pd.to_numeric(b['연도'], errors='coerce')
        b['65세이상인구'] = pd.to_numeric(b['65세이상인구'], errors='coerce')
        b['시도명'] = b['시도명'].replace(RENAME_REGION)
        result = result.merge(b[['연도', '시도명', '65세이상인구']],
                              on=['연도', '시도명'], how='left', validate='one_to_one')
        if result['65세이상인구'].isna().any() or (result['65세이상인구'] <= 0).any():
            print('B팀 인구 데이터 결측/0 발견. 해당 행 확인:')
            print(result[result['65세이상인구'].isna() | (result['65세이상인구'] <= 0)][['연도', '시도명', '65세이상인구']])
        else:
            result['고령사고_만명당'] = result['고령사고건수'] / result['65세이상인구'] * 10000
            has_population = True

# 4-9: 저장 (B팀 인구가 없어도 A팀 독립 산출물 저장)
base_cols = ['연도', '시도명', '고령사고건수', '전체사고건수',
             '고령사망자수', '전체사망자수', '고령치사율', '전체치사율']
if has_population:
    base_cols += ['65세이상인구', '고령사고_만명당']
result[base_cols].sort_values(['연도', '시도명']).to_csv(
    CLEAN / '정제_A_사고.csv', index=False, encoding='utf-8-sig')
print('\n[4-9] 저장 완료:', CLEAN / '정제_A_사고.csv')

# 5-2: 2024 시도별 치사율 막대 그래프
plot_2024 = result[result['연도'] == 2024].melt(
    id_vars='시도명', value_vars=['고령치사율', '전체치사율'],
    var_name='구분', value_name='치사율')
plt.figure(figsize=(13, 8))
sns.barplot(data=plot_2024, x='치사율', y='시도명', hue='구분')
plt.title('2024년 시도별 고령운전자 사고 vs 전체사고 치사율')
plt.xlabel('치사율 (%)')
plt.ylabel('시도명')
plt.tight_layout()
plt.savefig(GRAPHS / 'A_2024_치사율_비교.png', dpi=180)
plt.close()

# 5-2 보조: 전국 치사율 추이
national = result.groupby('연도', as_index=False)[['고령사고건수', '고령사망자수', '전체사고건수', '전체사망자수']].sum()
national['고령치사율'] = national['고령사망자수'] / national['고령사고건수'] * 100
national['전체치사율'] = national['전체사망자수'] / national['전체사고건수'] * 100
plt.figure(figsize=(8, 5))
plt.plot(national['연도'], national['고령치사율'], marker='o', label='고령운전자 사고')
plt.plot(national['연도'], national['전체치사율'], marker='o', label='전체 사고')
plt.xticks([2022, 2023, 2024])
plt.xlabel('연도')
plt.ylabel('치사율 (%)')
plt.title('2022~2024년 전국 사고 치사율 변화')
plt.legend()
plt.tight_layout()
plt.savefig(GRAPHS / 'A_전국_치사율_추이.png', dpi=180)
plt.close()

# 5-1: 고령인구 1만 명당 사고 격차
if has_population:
    plt.figure(figsize=(13, 9))
    sns.barplot(data=result, x='고령사고_만명당', y='시도명', hue='연도')
    plt.title('2022~2024년 시도별 고령 인구 1만 명당 고령운전자 사고')
    plt.xlabel('고령 인구 1만 명당 사고 건수')
    plt.ylabel('시도명')
    plt.tight_layout()
    plt.savefig(GRAPHS / 'A_고령사고_만명당_지역비교.png', dpi=180)
    plt.close()
    print('\n[가설 1] 연도별 최대/최소 격차')
    for year, g in result.groupby('연도'):
        minimum = g['고령사고_만명당'].min()
        maximum = g['고령사고_만명당'].max()
        ratio = maximum / minimum if minimum > 0 else np.nan
        print(f'{year}: 최소 {minimum:.2f}, 최대 {maximum:.2f}, 배율 {ratio:.2f}, 가설 충족: {ratio >= 2}')
else:
    print('\n[가설 1] B팀 65세 이상 인구 파일이 없어 만명당 사고 분석을 보류합니다.')

print('\n분석 완료. data/clean 및 graphs 폴더를 확인하세요.')
print('주의: 가설 3(반납률 상관분석)는 E팀 결합분석에서 검증합니다.')
