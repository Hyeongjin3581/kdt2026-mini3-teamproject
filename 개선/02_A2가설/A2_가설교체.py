# [개인 보완] 회고 ④ A-2 가설 교체
# 실행: 저장소 최상위에서 python "개선/02_A2가설/A2_가설교체.py"
#
# 기존 A-2: "고령운전자 사고 치사율은 17개 시도 모두에서 전체 사고보다 높을 것이다." → 45/51 충족, 기각
#   → 치사율은 '왜 반납이 중요한가'를 보여 주는 배경 근거이지, '반납을 가로막는 교통 공백'과 이어지는 가설이 아니었다.
#
# 새 A-2 (주제 연결): "2022년 반납률이 낮은 시도일수록 2022→2024년 고령운전자 사고(65세 이상 인구 1만 명당)가 더 빠르게 늘었을 것이다."
#   판정 기준: r ≤ -0.4 (팀 공통 기준과 동일) + 세종 제외 민감도 확인 (세종은 인구가 작고 신도시라 값이 크게 튐)

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

출력 = '개선/02_A2가설'
결합 = pd.read_csv('data/merge/결합테이블.csv')
사고 = pd.read_csv('data/정제_A_사고.csv')

# 1. 기존 A-2 재확인 (치사율)
기존충족 = int(사고['H2_조건충족'].sum())
예외 = 사고.loc[~사고['H2_조건충족'], ['연도', '시도명', '고령치사율', '전체치사율']]
print(f'[기존 A-2] 고령 치사율 > 전체 치사율: {기존충족}/{len(사고)} → 기각')
print(예외.round(2).to_string(index=False))

# 2. 새 A-2 데이터: 시도별 2022 반납률, 2022→2024 사고 증가율
반납 = 결합.pivot(index='시도명', columns='연도', values='반납률')
만명당 = 결합.pivot(index='시도명', columns='연도', values='고령사고_만명당')
표 = pd.DataFrame({
    '반납률_2022': 반납[2022],
    '반납률_2024': 반납[2024],
    '사고만명당_2022': 만명당[2022],
    '사고만명당_2024': 만명당[2024],
})
표['사고증가율(%)'] = (표['사고만명당_2024'] / 표['사고만명당_2022'] - 1) * 100
표['반납률변화율(%)'] = (표['반납률_2024'] / 표['반납률_2022'] - 1) * 100
표 = 표.sort_values('반납률_2022')


def 상관(t, x, y='사고증가율(%)'):
    r, p = pearsonr(t[x], t[y])
    rs, ps = spearmanr(t[x], t[y])
    return {'피어슨 r': round(r, 3), 'p': round(p, 3), '스피어만 ρ': round(rs, 3), 'p(스피어만)': round(ps, 3), 'n': len(t)}


세종제외 = 표.drop('세종특별자치시')
결과 = pd.DataFrame([
    {'분석': '새 A-2: 2022 반납률 ↔ 사고 증가율 (전체)', **상관(표, '반납률_2022')},
    {'분석': '새 A-2: 2022 반납률 ↔ 사고 증가율 (세종 제외)', **상관(세종제외, '반납률_2022')},
    {'분석': '보조: 반납률 변화율 ↔ 사고 증가율 (전체)', **상관(표, '반납률변화율(%)')},
    {'분석': '보조: 반납률 변화율 ↔ 사고 증가율 (세종 제외)', **상관(세종제외, '반납률변화율(%)')},
])
판정 = '채택' if (결과.loc[0, '피어슨 r'] <= -0.4 and 결과.loc[1, '피어슨 r'] <= -0.4) else '기각'
print('\n[새 A-2]')
print(결과.to_string(index=False))
print('판정:', 판정)
print('\n[시도별 값]')
print(표.round(1).to_string())

# 3. 그래프: 산점도 (세종 강조, 전체 / 세종 제외 추세선)
#   평소에는 3그룹 막대를 썼지만, 여기서는 '한 지역(세종)이 상관을 만든다'는 점을 보여 줘야 해서 점 하나하나가 보이는 산점도를 쓴다.
fig, ax = plt.subplots(figsize=(10, 6.5))
기타 = 표.drop('세종특별자치시')
ax.scatter(기타['반납률_2022'], 기타['사고증가율(%)'], s=70, color='#4C72B0', label='16개 시도')
ax.scatter(표.loc['세종특별자치시', '반납률_2022'], 표.loc['세종특별자치시', '사고증가율(%)'],
           s=110, color='#C44E52', label='세종 (인구가 작고 값이 튐)', zorder=3)
짧은 = {s: s.replace('특별자치', '').replace('광역시', '').replace('특별시', '').rstrip('도시')
       .replace('충청북', '충북').replace('충청남', '충남').replace('전라남', '전남').replace('경상북', '경북')
       .replace('경상남', '경남').replace('전북', '전북').replace('강원', '강원') for s in 표.index}
for s, r in 표.iterrows():
    위치 = (-30, -14) if s == '인천광역시' else (5, 4)          # 광주와 겹치지 않게
    ax.annotate(짧은[s], (r['반납률_2022'], r['사고증가율(%)']), xytext=위치, textcoords='offset points', fontsize=10)
xs = np.linspace(표['반납률_2022'].min() - 0.5, 표['반납률_2022'].max() + 0.5, 50)
for t, 색, 선, 라벨 in [(표, 'gray', '--', f"전체 추세 (r = {결과.loc[0, '피어슨 r']:.2f})"),
                       (세종제외, '#1F4E79', '-', f"세종 제외 추세 (r = {결과.loc[1, '피어슨 r']:.2f})")]:
    기울기, 절편 = np.polyfit(t['반납률_2022'], t['사고증가율(%)'], 1)
    ax.plot(xs, 기울기 * xs + 절편, 선, color=색, linewidth=1.8, label=라벨)
ax.axhline(0, color='gray', linewidth=0.8)
ax.set_xlabel('2022년 반납률 (65세 이상 천 명당 건)')
ax.set_ylabel('2022→2024년 고령운전자 사고 증가율 (인구 1만 명당 기준, %)')
ax.set_title(f'새 A-2: 반납률이 낮은 시도일수록 사고가 더 빨리 늘었나? → {판정}', fontsize=13, fontweight='bold')
ax.legend(loc='upper right', fontsize=10)
plt.tight_layout()
fig.savefig(f'{출력}/A2_반납률_사고증가율_산점도.png', dpi=150, facecolor='white')

# 4. 결과 저장
def 마크다운(df, index=True):
    d = df.reset_index().rename(columns={'index': '시도명'}) if index else df
    def 칸(v):
        return f'{v:,.1f}' if isinstance(v, float) else str(v)
    줄 = ['| ' + ' | '.join(map(str, d.columns)) + ' |', '|' + '---|' * len(d.columns)]
    줄 += ['| ' + ' | '.join(칸(v) for v in r) + ' |' for r in d.itertuples(index=False)]
    return '\n'.join(줄)


with open(f'{출력}/결과표.md', 'w', encoding='utf-8') as f:
    f.write('# 회고 ④ A-2 가설 교체 — 결과표\n\n')
    f.write(f'## 기존 A-2 (치사율)\n\n고령 치사율 > 전체 치사율: {기존충족}/{len(사고)} → 기각\n\n')
    f.write(마크다운(예외.round(2), index=False) + '\n\n')
    f.write('## 새 A-2 상관 분석\n\n')
    결과표 = 결과.copy()
    for c in ['피어슨 r', 'p', '스피어만 ρ', 'p(스피어만)']:
        결과표[c] = 결과표[c].map(lambda v: f'{v:.3f}')
    f.write(마크다운(결과표, index=False) + f'\n\n판정: **{판정}**\n\n')
    f.write('## 시도별 값 (2022 반납률 오름차순)\n\n')
    f.write(마크다운(표.round(1)) + '\n')
print(f'\n저장: {출력}/결과표.md, {출력}/A2_반납률_사고증가율_산점도.png')
