# [개인 보완] 회고 ① B안 (2) 반납 지원 조례 → 시도·연도 변수 → 반납률과 비교
# 실행: 저장소 최상위에서 python "개선/05_조례/02_조례분석.py"
#
# 1) 관련 조례 판정: 본문에 '면허 (자진)반납' + '지원' + 고령 표현이 함께 있는 조례
#    - 핵심 조례: 제목에 '고령운전자' 또는 '운전면허' (반납 지원을 직접 다루는 조례)
#    - 부가 조례: 그 밖의 조례 안에 반납자 혜택 조항이 있는 경우 (예: 주차·수수료 감면) → 따로 표시만
# 2) 지원 내용: '반납' 주변 글에서 금액(○만 원)과 방식(교통카드·지역화폐·상품권 등)을 뽑는다
# 3) 시도·연도 변수 (각 연도 12월 31일 기준, 최초 공포일 이전이면 '없음')
#    - 광역조례: 시도 자체 조례가 있는가 (0/1)
#    - 시군구조례비율: 시군구 중 핵심 조례가 있는 곳의 비율 (세종·제주는 시군구가 없어 광역조례 값 사용)
# 4) 반납률과의 상관·그룹 비교 (팀 판정 기준 |r| ≥ 0.4, 표본 17개라 스피어만·세종 제외도 함께)

import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

출력 = '개선/05_조례'
d = pd.read_csv(f'{출력}/조례_원자료.csv', dtype=str).fillna('')
결합 = pd.read_csv('data/merge/결합테이블.csv')

# 시도 이름 맞추기 (옛 이름 포함)
시도표 = {'서울특별시': '서울특별시', '부산광역시': '부산광역시', '대구광역시': '대구광역시', '인천광역시': '인천광역시',
        '광주광역시': '광주광역시', '대전광역시': '대전광역시', '울산광역시': '울산광역시', '세종특별자치시': '세종특별자치시',
        '경기도': '경기도', '강원도': '강원특별자치도', '강원특별자치도': '강원특별자치도', '충청북도': '충청북도',
        '충청남도': '충청남도', '전라북도': '전북특별자치도', '전북특별자치도': '전북특별자치도', '전라남도': '전라남도',
        '경상북도': '경상북도', '경상남도': '경상남도', '제주특별자치도': '제주특별자치도'}
시군구수 = {'서울특별시': 25, '부산광역시': 16, '대구광역시': 9, '인천광역시': 10, '광주광역시': 5, '대전광역시': 5,
         '울산광역시': 5, '세종특별자치시': 0, '경기도': 31, '강원특별자치도': 18, '충청북도': 11, '충청남도': 15,
         '전북특별자치도': 14, '전라남도': 22, '경상북도': 22, '경상남도': 18, '제주특별자치도': 0}   # 2024년 기준 (합계 226)
조각 = d['지자체기관명'].str.split()
d['시도'] = 조각.str[0].map(시도표)
d['기초'] = 조각.str[1].fillna('')
d['광역여부'] = d['기초'] == ''

# 1) 관련 조례 판정
반납 = r'(자진\s?반납|면허\s?(를|증)?\s?(자진)?\s?반납|반납\s?(한|하는)\s?(사람|자|고령))'
고령 = r'65세|70세|고령|어르신|노인'   # 정규식 경고를 피하려고 아래 str.contains 는 regex=True 로 그대로 둔다
d['반납지원'] = d['본문'].str.contains(반납) & d['본문'].str.contains('지원') & d['본문'].str.contains(고령)
d['핵심'] = d['반납지원'] & (d['자치법규종류'] == '조례') & d['자치법규명'].str.contains('고령운전자|운전면허|고령자\s?교통|노인\s?교통|어르신\s?교통')
d['구분'] = np.select([d['핵심'], d['반납지원']], ['핵심 조례', '부가 조례'], '무관')


# 2) 지원 내용
def 반납주변(글, 폭=250):
    return ' '.join(글[max(0, m.start() - 폭): m.end() + 폭] for m in re.finditer(반납, 글))


def 금액(글):
    금 = [int(x) for x in re.findall(r'(\d{1,3})\s?만\s?원', 반납주변(글))]
    return max(금) if 금 else np.nan


방식사전 = {'교통카드': r'교통\s?카드|선불\s?카드|교통비', '지역화폐': r'지역\s?화폐|지역\s?사랑\s?상품권|상품권|페이',
          '택시·버스': r'택시|버스\s?이용|수요응답', '현금·기타': r'현금|물품'}
d['지원금액(만원)'] = d['본문'].map(금액)
for k, p in 방식사전.items():
    d[k] = d['본문'].map(lambda g, p=p: bool(re.search(p, 반납주변(g))))
# 부칙이 여러 개면 공포일자가 목록 문자열로 들어 있으므로 8자리 날짜를 모두 찾아 가장 이른 날을 최초 공포일로 쓴다
d['최초공포'] = pd.to_datetime(d['최초공포일자'].map(lambda x: min(re.findall(r'(?:19|20)\d{6}', x), default='')),
                           format='%Y%m%d', errors='coerce')

핵심 = d[d['구분'] == '핵심 조례'].copy()
print('수집 조례:', len(d), '/ 구분:', d['구분'].value_counts().to_dict())
print('핵심 조례 최초 공포 연도:', 핵심['최초공포'].dt.year.value_counts().sort_index().to_dict())
print('핵심 조례 지원금액(만원) 분포:', 핵심['지원금액(만원)'].describe().round(1).to_dict())

# 3) 시도·연도 변수
행 = []
for 시도, 수 in 시군구수.items():
    for 연도 in [2022, 2023, 2024]:
        기준일 = pd.Timestamp(f'{연도}-12-31')
        유효 = 핵심[(핵심['시도'] == 시도) & (핵심['최초공포'] <= 기준일)]
        광역 = int(유효['광역여부'].any())
        기초수 = 유효.loc[~유효['광역여부'], '기초'].nunique()
        비율 = 기초수 / 수 if 수 else float(광역)
        금 = 유효['지원금액(만원)'].dropna()
        행.append({'시도명': 시도, '연도': 연도, '광역조례': 광역, '조례시군구수': 기초수, '시군구수': 수,
                  '시군구조례비율': 비율, '조례지원금액중앙값': 금.median() if len(금) else np.nan})
변수 = pd.DataFrame(행)
표 = 결합.merge(변수, on=['시도명', '연도'], how='left')
print('\n[3] 2024년 시도별 조례 현황')
print(표[표['연도'] == 2024][['시도명', '광역조례', '조례시군구수', '시군구수', '시군구조례비율', '조례지원금액중앙값', '반납률']]
      .sort_values('반납률', ascending=False).round(2).to_string(index=False))

# 4) 반납률과 비교
결과 = []
for 연도 in [2022, 2023, 2024]:
    t = 표[표['연도'] == 연도]
    for x in ['시군구조례비율', '광역조례']:
        r, p = pearsonr(t[x], t['반납률'])
        t2 = t[t['시도명'] != '세종특별자치시']
        결과.append({'연도': 연도, '변수': x, 'r': round(r, 3), 'p': round(p, 3),
                    '스피어만 ρ': round(spearmanr(t[x], t['반납률'])[0], 3),
                    'r(세종 제외)': round(pearsonr(t2[x], t2['반납률'])[0], 3)})
    g = t.groupby('광역조례')['반납률'].mean()
    print(f'{연도} 광역조례 있음/없음 평균 반납률:', g.round(2).to_dict())
결과 = pd.DataFrame(결과)
print('\n[4] 조례 변수 ↔ 반납률')
print(결과.to_string(index=False))

# 저장
d.drop(columns=['본문']).to_csv(f'{출력}/조례_분류.csv', index=False, encoding='utf-8-sig')
변수.to_csv(f'{출력}/시도연도_조례변수.csv', index=False, encoding='utf-8-sig')
결과.to_csv(f'{출력}/조례_반납률_상관.csv', index=False, encoding='utf-8-sig')

# 그래프: 2024 시군구조례비율 vs 반납률
t = 표[표['연도'] == 2024]
fig, ax = plt.subplots(figsize=(9.5, 6))
색 = np.where(t['시도명'].str.contains('특별시|광역시|특별자치시'), '#4C72B0', '#C44E52')
ax.scatter(t['시군구조례비율'] * 100, t['반납률'], c=색, s=70)
for _, r in t.iterrows():
    ax.annotate(r['시도명'].replace('특별자치', '').replace('광역시', '').replace('특별시', ''),
                (r['시군구조례비율'] * 100, r['반납률']), xytext=(4, 3), textcoords='offset points', fontsize=9)
rr = 결과[(결과['연도'] == 2024) & (결과['변수'] == '시군구조례비율')].iloc[0]
ax.set_xlabel('반납 지원 조례가 있는 시군구 비율 (%, 세종·제주는 광역 조례 여부)')
ax.set_ylabel('반납률 (65세 이상 천 명당)')
ax.set_title(f'2024년 반납 지원 조례 보급률과 반납률  r = {rr["r"]:.2f}, ρ = {rr["스피어만 ρ"]:.2f}', fontsize=13, fontweight='bold')
ax.scatter([], [], c='#4C72B0', label='특별·광역시')
ax.scatter([], [], c='#C44E52', label='도')
ax.legend(fontsize=10)
plt.tight_layout()
fig.savefig(f'{출력}/조례보급률_반납률_2024.png', dpi=150, facecolor='white')
print(f'\n저장: {출력}/조례_분류.csv, 시도연도_조례변수.csv, 조례_반납률_상관.csv, 조례보급률_반납률_2024.png')

# ─────────────────────────────────────────────
# 5) 제정일 한계 보완: 상한 시나리오 (현재 시행 중인 핵심 조례를 모두 '있음'으로)
#    현행 자치법규 본문의 부칙에는 '일부개정' 조례의 최초 제정일이 빠진 경우가 많다(핵심 182건 중 일부개정 93건).
#    그래서 위 연도별 변수는 실제보다 적게 잡힌 '하한'이다. 반대로 현재 보유 조례를 모두 있다고 보면 '상한'이 된다.
#    두 시나리오에서 결론이 같으면 제정일 문제는 결론을 바꾸지 않는다.
# ─────────────────────────────────────────────
상한행 = []
for 시도, 수 in 시군구수.items():
    t = 핵심[핵심['시도'] == 시도]
    광역 = int(t['광역여부'].any())
    상한행.append({'시도명': 시도, '광역조례': 광역, '시군구조례비율': (t.loc[~t['광역여부'], '기초'].nunique() / 수) if 수 else float(광역)})
상한 = pd.DataFrame(상한행)
상한결과 = []
for 연도 in [2022, 2023, 2024]:
    t = 결합[결합['연도'] == 연도].merge(상한, on='시도명')
    for x in ['시군구조례비율', '광역조례']:
        r, p = pearsonr(t[x], t['반납률'])
        상한결과.append({'연도': 연도, '변수': x, 'r': round(r, 3), 'p': round(p, 3), '스피어만 ρ': round(spearmanr(t[x], t['반납률'])[0], 3)})
상한결과 = pd.DataFrame(상한결과)
print('\n[5] 상한 시나리오 (현재 보유 조례 전부) ↔ 반납률')
print(상한결과.to_string(index=False))
print('\n두 시나리오 모두 |r| < 0.4:', bool((결과['r'].abs() < 0.4).all() and (상한결과['r'].abs() < 0.4).all()))
상한결과.to_csv(f'{출력}/조례_반납률_상관_상한.csv', index=False, encoding='utf-8-sig')
상한.to_csv(f'{출력}/시도_현재조례보유.csv', index=False, encoding='utf-8-sig')
