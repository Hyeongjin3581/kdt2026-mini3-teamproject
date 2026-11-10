# [개인 보완] 회고 ④ 다듬기 — 새 A-2 판정이 얼마나 튼튼한가
# 실행: 저장소 최상위에서 python "개선/02_A2가설/A2_민감도분석.py"
#
# A2_가설교체.py 에서 새 A-2 는 r = -0.35 로 기각, 세종을 빼면 +0.20 으로 방향이 바뀌었다.
# 여기서는 세 가지를 더 확인한다.
#   ① 한 지역씩 빼고 r 다시 계산 (leave-one-out): 세종만 특별한가, 다른 지역도 판정을 흔드는가
#   ② 2개 시점(2022·2024) 증가율 대신 3년 추세 기울기: 중간 연도(2023)를 버리지 않으면 결과가 달라지는가
#   ③ 연도별 변화량을 묶어서 보기 (지역 안에서 반납률이 오른 해에 사고가 덜 늘었나): 탐색용

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import pearsonr, spearmanr, linregress

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

출력 = '개선/02_A2가설'
결합 = pd.read_csv('data/merge/결합테이블.csv')
반납 = 결합.pivot(index='시도명', columns='연도', values='반납률')
사고 = 결합.pivot(index='시도명', columns='연도', values='고령사고_만명당')
증가율 = (사고[2024] / 사고[2022] - 1) * 100
기준 = -0.4
세종 = '세종특별자치시'
줄 = ['# 회고 ④ 다듬기 — 새 A-2 민감도 분석\n', '`A2_민감도분석.py` 실행 결과\n']

# ① leave-one-out
loo = pd.Series({s: pearsonr(반납[2022].drop(s), 증가율.drop(s))[0] for s in 반납.index}).sort_values()
전체r = pearsonr(반납[2022], 증가율)[0]
print('[①] 한 지역씩 뺀 r')
print(loo.round(3).to_string())
줄 += ['## ① 한 지역씩 빼고 다시 계산 (leave-one-out)\n',
       f'전체 r = {전체r:.3f}. 지역 하나를 뺄 때 r 범위: **{loo.min():.3f} ({loo.idxmin()} 제외) ~ {loo.max():.3f} ({loo.idxmax()} 제외)**\n',
       '| 뺀 지역 | r | 기준(≤ −0.4) |', '|---|---|---|']
줄 += [f'| {s} | {v:.3f} | {"충족" if v <= 기준 else "미충족"} |' for s, v in loo.items()]
줄.append('')

fig, ax = plt.subplots(figsize=(10, 6))
색 = ['#C44E52' if s == 세종 else ('#1F4E79' if v <= 기준 else '#9AA5B1') for s, v in loo.items()]
막대 = ax.barh([s.replace('특별자치', '').replace('광역시', '').replace('특별시', '') for s in loo.index], loo.values, color=색)
ax.bar_label(막대, fmt='%.2f', padding=3, fontsize=9)
ax.axvline(전체r, color='black', linestyle='--', linewidth=1, label=f'전체 r = {전체r:.2f}')
ax.axvline(기준, color='#C44E52', linestyle=':', linewidth=1.5, label='판정 기준 -0.4')
ax.axvline(0, color='gray', linewidth=0.8)
ax.set_xlim(-0.7, 0.4)
ax.set_xlabel('그 지역을 뺐을 때의 상관계수 r')
ax.set_title('지역 하나만 빼도 판정이 바뀐다: 대전을 빼면 -0.52(충족), 세종을 빼면 +0.20', fontsize=12, fontweight='bold')
ax.legend(loc='lower right', fontsize=10)
plt.tight_layout()
fig.savefig(f'{출력}/A2_한지역제외_상관계수.png', dpi=150, facecolor='white')
plt.close(fig)

# ② 3년 추세 기울기
기울기 = 사고.apply(lambda r: linregress([2022, 2023, 2024], r.values).slope, axis=1)       # 만 명당 건/년
상대기울기 = 기울기 / 사고[2022] * 100                                                     # %/년
줄 += ['## ② 2개 시점 증가율 대신 3년 추세 기울기\n', '| 종속변수 | r (전체) | p | 스피어만 ρ | r (세종 제외) |', '|---|---|---|---|---|']
print('\n[②] 3년 추세')
for 이름, y in [('2022→2024 증가율(%)', 증가율), ('3년 추세 기울기(만 명당 건/년)', 기울기), ('3년 상대 기울기(%/년)', 상대기울기)]:
    r, p = pearsonr(반납[2022], y)
    rs = spearmanr(반납[2022], y)[0]
    r2 = pearsonr(반납[2022].drop(세종), y.drop(세종))[0]
    print(f'{이름}: r={r:.3f} p={p:.3f} ρ={rs:.3f} | 세종 제외 r={r2:.3f}')
    줄.append(f'| {이름} | {r:.3f} | {p:.3f} | {rs:.3f} | {r2:.3f} |')
줄.append('')

# ③ 연도별 변화량 묶음 (탐색)
변화 = []
for a, b in [(2022, 2023), (2023, 2024)]:
    d = pd.DataFrame({'반납률변화': 반납[b] - 반납[a], '사고변화': 사고[b] - 사고[a]})
    d['구간'] = f'{a}→{b}'
    변화.append(d)
변화 = pd.concat(변화)
줄 += ['## ③ 연도별 변화량을 묶어서 보기 (탐색)\n',
       '같은 지역 안에서 "반납률이 오른 해에 사고가 덜 늘었나"를 본다. 지역마다 2개 구간이라 관측치가 서로 독립이 아니고, 결과를 본 뒤 추가한 분석이므로 **판정에는 쓰지 않는다.**\n',
       '| 범위 | n | r | p | 스피어만 ρ |', '|---|---|---|---|---|']
print('\n[③] 연도별 변화량 묶음')
for 이름, t in [('전체', 변화), ('세종 제외', 변화.drop(세종)),
               ('세종 제외 · 2022→2023', 변화.drop(세종).query("구간 == '2022→2023'")),
               ('세종 제외 · 2023→2024', 변화.drop(세종).query("구간 == '2023→2024'"))]:
    r, p = pearsonr(t['반납률변화'], t['사고변화'])
    rs = spearmanr(t['반납률변화'], t['사고변화'])[0]
    print(f'{이름}: n={len(t)} r={r:.3f} p={p:.3f} ρ={rs:.3f}')
    줄.append(f'| {이름} | {len(t)} | {r:.3f} | {p:.3f} | {rs:.3f} |')
줄.append('')

with open(f'{출력}/민감도_결과.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(줄))
print(f'\n저장: {출력}/민감도_결과.md, {출력}/A2_한지역제외_상관계수.png')
