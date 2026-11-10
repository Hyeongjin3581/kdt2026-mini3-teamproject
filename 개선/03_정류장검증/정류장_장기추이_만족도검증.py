# [개인 보완] 회고 ② 정류장 검증 (2) — 장기 추이로 급변값 확인 + 배차간격 만족도로 해석 ① 확인
# 실행: 저장소 최상위에서 python "개선/03_정류장검증/정류장_장기추이_만족도검증.py"
#
# 원자료 (공공데이터포털, 한국교통안전공단 · 대중교통현황조사, 「대중교통의 육성 및 이용촉진에 관한 법률」 제16조)
#   - 전국 대중교통 버스정류장 현황 (data.go.kr/data/15066754): 2018~2021 과거 파일(원자료 폴더) + 2022~2024 팀 데이터
#   - 전국 지역별 대중교통 서비스별 만족도 현황 (data.go.kr/data/15066827): 2021·2022·2023·2025 (2024년 파일은 공개 목록에 없음)
#     만족도는 7점 만점, 대중교통 이용자 설문 결과
#
# 확인할 것
#   ① 급변값이 2023·2024년만의 일인가, 원래 자주 있는 일인가 → 2018~2024 전년 대비 증감률
#   ② 해석 ① "도 지역은 정류장은 많지만 버스가 자주 오지 않는다" → 배차간격 적절성 만족도로 확인 (2022·2023: 반납률과 같은 해)

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

출력 = '개선/03_정류장검증'
원자료 = f'{출력}/원자료'
정식 = {'서울': '서울특별시', '부산': '부산광역시', '대구': '대구광역시', '인천': '인천광역시', '광주': '광주광역시',
      '대전': '대전광역시', '울산': '울산광역시', '세종': '세종특별자치시', '경기': '경기도', '강원': '강원특별자치도',
      '충북': '충청북도', '충남': '충청남도', '전북': '전북특별자치도', '전남': '전라남도', '경북': '경상북도',
      '경남': '경상남도', '제주': '제주특별자치도'}
짧게 = {v: k for k, v in 정식.items()}
결합 = pd.read_csv('data/merge/결합테이블.csv')
줄 = ['# 회고 ② 정류장 검증 (2) — 장기 추이 · 배차간격 만족도\n', '`정류장_장기추이_만족도검증.py` 실행 결과\n']

# ─────────────────────────────────────────────
# ① 2018~2024 정류장 수 장기 추이
# ─────────────────────────────────────────────
연도별 = {}
for y in [2018, 2019, 2020, 2021]:
    d = pd.read_csv(f'{원자료}/정류장_{y}1231.csv')
    d['전체버스정류장'] = pd.to_numeric(d['전체버스정류장'].astype(str).str.strip())
    연도별[y] = d.set_index('구분')['전체버스정류장']
팀 = 결합.pivot(index='시도명', columns='연도', values='전체버스정류장').rename(index=짧게)
for y in [2022, 2023, 2024]:
    연도별[y] = 팀[y]
장기 = pd.DataFrame(연도별).loc[list(정식)]
증감 = (장기.pct_change(axis=1) * 100).drop(columns=2018)
급변수 = (증감.abs() > 10).sum()
print('[①] 연도별 ±10% 초과 급변 시도 수')
print(급변수.to_string())
print('\n전국 합계:', 장기.sum().astype(int).to_dict())
줄 += ['## ① 2018~2024 정류장 수 장기 추이\n', '연도별로 전년 대비 ±10% 넘게 바뀐 시도 수:\n',
       '| 연도 | ' + ' | '.join(str(c) for c in 급변수.index) + ' |', '|---|' + '---|' * len(급변수),
       '| 급변 시도 수 | ' + ' | '.join(str(v) for v in 급변수.values) + ' |', '',
       '전국 합계: ' + ', '.join(f'{y}년 {v:,}개' for y, v in 장기.sum().astype(int).items()) + '\n',
       '눈에 띄는 예: ' + ', '.join(f'{s} {y}년 {증감.loc[s, y]:+.0f}%' for s, y in
                              [('서울', 2021), ('부산', 2020), ('대전', 2019), ('대전', 2020), ('충남', 2019), ('강원', 2019)]) + '\n']

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(증감, annot=True, fmt='+.0f', cmap='RdBu_r', center=0, vmin=-40, vmax=40, linewidths=0.5,
            cbar_kws={'label': '전년 대비 증감률(%)'}, ax=ax, annot_kws={'size': 9})
ax.set_title('버스정류장 수 전년 대비 증감률 (2019~2024): 큰 폭의 변동이 해마다 반복된다', fontsize=12, fontweight='bold')
ax.set_xlabel('')
ax.set_ylabel('')
plt.tight_layout()
fig.savefig(f'{출력}/정류장_장기_증감률_히트맵.png', dpi=150, facecolor='white')
plt.close(fig)

# ─────────────────────────────────────────────
# ② 배차간격 만족도로 해석 ① 확인
# ─────────────────────────────────────────────
def 만족도(y, 항목):
    s = pd.read_csv(f'{원자료}/만족도_{y}1231.csv')
    s['구분2'] = s['구분2'].str.replace(' ', '')
    if 항목 not in s['구분2'].values:
        return None
    return s.loc[s['구분2'] == 항목].iloc[0, 2:].astype(float).rename(index=정식)


행, 평균행 = [], []
for y in [2022, 2023]:
    t = 결합[결합['연도'] == y].set_index('시도명').copy()
    t['배차간격'] = 만족도(y, '배차간격적절성')
    t['유형'] = np.where(t.index.str.contains('특별시|광역시|특별자치시'), '특별·광역시', '도')
    평균 = t.groupby('유형')['배차간격'].mean()
    평균행.append({'연도': y, '특별·광역시': round(평균['특별·광역시'], 2), '도': round(평균['도'], 2)})
    for a, b, 뜻 in [('정류장_천명당', '배차간격', '정류장 많은 곳일수록 배차 만족도 낮은가 (해석 ①)'),
                    ('배차간격', '반납률', '배차 만족도 높은 곳일수록 반납률 높은가'),
                    ('정류장_천명당', '반납률', '(참고) 기존 결과')]:
        r, p = pearsonr(t[a], t[b])
        행.append({'연도': y, '관계': f'{a} ↔ {b}', '확인 내용': 뜻, 'r': round(r, 3), 'p': round(p, 3),
                  '스피어만 ρ': round(spearmanr(t[a], t[b])[0], 3)})
    if y == 2023:
        t['접근'] = 만족도(y, '접근거리및시간')
        r, p = pearsonr(t['접근'], t['반납률'])
        행.append({'연도': y, '관계': '접근거리및시간 ↔ 반납률', '확인 내용': '정류장까지 가기 편한 곳일수록 반납률 높은가',
                  'r': round(r, 3), 'p': round(p, 3), '스피어만 ρ': round(spearmanr(t['접근'], t['반납률'])[0], 3)})
    if y == 2022:
        그림자료 = t.copy()
결과 = pd.DataFrame(행)
평균표 = pd.DataFrame(평균행)
print('\n[②] 배차간격 적절성 만족도 (7점 만점) 지역 유형별 평균')
print(평균표.to_string(index=False))
print(결과.to_string(index=False))

줄 += ['## ② 배차간격 만족도로 해석 ① 확인\n', '배차간격 적절성 만족도(7점 만점) 지역 유형별 평균:\n',
       '| 연도 | 특별·광역시 | 도 |', '|---|---|---|'] + [f'| {a} | {b} | {c} |' for a, b, c in 평균표.itertuples(index=False)] + ['']
줄 += ['| 연도 | 관계 | 확인 내용 | r | p | 스피어만 ρ |', '|---|---|---|---|---|---|']
줄 += [f'| {a} | {b} | {c} | {d:.3f} | {e:.3f} | {g:.3f} |' for a, b, c, d, e, g in 결과.itertuples(index=False)]
줄 += ['', '- 배차간격 만족도는 대도시와 도 지역의 차이가 거의 없고, 정류장 수·반납률과의 상관도 약하다(|r| < 0.4).',
       '- 따라서 해석 ① "도 지역은 버스가 자주 오지 않아 반납이 적다"는 **이 데이터로는 지지되지 않는다.**',
       '- 다만 만족도는 버스 이용자의 주관적 평가라 실제 배차간격(분)과 다를 수 있다. 버스를 거의 타지 않는 어르신(반납을 망설이는 사람)의 의견은 담기지 않는다.\n']

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
for ax, (x, y, 제목) in zip(axes, [('정류장_천명당', '배차간격', '정류장 수 ↔ 배차간격 만족도 (2022)'),
                                  ('배차간격', '반납률', '배차간격 만족도 ↔ 반납률 (2022)')]):
    색 = np.where(그림자료['유형'] == '도', '#C44E52', '#4C72B0')
    ax.scatter(그림자료[x], 그림자료[y], c=색, s=60)
    for s, rr in 그림자료.iterrows():
        ax.annotate(짧게[s], (rr[x], rr[y]), xytext=(4, 3), textcoords='offset points', fontsize=9)
    r = pearsonr(그림자료[x], 그림자료[y])[0]
    ax.set_title(f'{제목}  r = {r:.2f}', fontsize=12)
    ax.set_xlabel('어르신 천 명당 정류장(개)' if x == '정류장_천명당' else '배차간격 적절성 만족도 (7점)')
    ax.set_ylabel('배차간격 적절성 만족도 (7점)' if y == '배차간격' else '반납률 (65세 이상 천 명당)')
axes[0].scatter([], [], c='#4C72B0', label='특별·광역시')
axes[0].scatter([], [], c='#C44E52', label='도')
axes[0].legend(loc='lower left', fontsize=10)
fig.suptitle('해석 ① 확인: 배차간격 만족도는 지역 유형·정류장 수·반납률과 뚜렷한 관계가 없다', fontsize=13, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{출력}/배차간격_만족도_검증.png', dpi=150, facecolor='white')

with open(f'{출력}/장기추이_만족도_결과.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(줄))
print(f'\n저장: {출력}/장기추이_만족도_결과.md, 정류장_장기_증감률_히트맵.png, 배차간격_만족도_검증.png')
