# [개인 보완] 회고 ② 정류장 데이터 검증 — 급변값을 어떻게 처리해도 결론(정류장 ↔ 반납률 음의 관계)이 유지되는가
# 실행: 저장소 최상위에서 python "개선/03_정류장검증/정류장_민감도분석.py"
#
# 배경: 정류장 수가 1년 새 ±10% 넘게 바뀐 시도·연도가 9건 있었다(예: 대전 2023 -15.1% → 2024 +19.2%).
#       공공데이터포털 원본 페이지(한국교통안전공단_전국 대중교통 버스정류장 현황)에는 조사 방법 변경 안내가 없어
#       원인은 확인할 수 없었다. 그래서 "처리 방식을 바꿔도 결론이 같은가"로 검증한다.
#
# 처리 방식
#   A. 원본 그대로
#   B. 급변 시도를 그해 분석에서 제외
#   C. 급변값을 앞뒤 연도 평균으로 보정 (대전 2023처럼 튀었다 돌아온 경우에 해당)
#   D. 3년 평균 정류장_천명당 사용 (한 해의 집계 흔들림을 줄임)
#   E. 순위 기반(스피어만) 상관
#   F. 한 지역씩 빼고 다시 계산 (leave-one-out) → 범위

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
결합 = pd.read_csv('data/merge/결합테이블.csv')
연도들 = [2022, 2023, 2024]

정류장 = 결합.pivot(index='시도명', columns='연도', values='전체버스정류장')
고령인구 = 결합.pivot(index='시도명', columns='연도', values='65세이상인구')
반납률 = 결합.pivot(index='시도명', columns='연도', values='반납률')
천명당 = 정류장 / 고령인구 * 1000

# 1. 급변 시도·연도 찾기 (전년 대비 ±10% 초과) — 2022년은 전년 자료가 없어 2023·2024만 판단
변화 = 정류장.pct_change(axis=1) * 100
급변 = [(s, y, round(변화.loc[s, y], 1)) for y in [2023, 2024] for s in 정류장.index if abs(변화.loc[s, y]) > 10]
print('[1] 급변 시도·연도 (전년 대비 ±10% 초과):', len(급변), '건')
for s, y, v in 급변:
    print(f'  {y} {s}: {v:+.1f}%')

# 2. 처리 방식별 연도 r
보정 = 정류장.astype(float)
for s, y, _ in 급변:
    앞, 뒤 = y - 1, y + 1
    if 뒤 in 정류장.columns:                     # 앞뒤 연도가 모두 있으면 평균으로 보정 (2023만 해당)
        보정.loc[s, y] = (정류장.loc[s, 앞] + 정류장.loc[s, 뒤]) / 2
보정천명당 = 보정 / 고령인구 * 1000
평균천명당 = 천명당.mean(axis=1)


def r(x, y):
    return pearsonr(x, y)[0]


행 = []
for y in 연도들:
    제외 = [s for s, yy, _ in 급변 if yy == y]
    남은 = 천명당.index.difference(제외)
    loo = [r(천명당[y].drop(s), 반납률[y].drop(s)) for s in 천명당.index]
    행.append({
        '연도': y,
        'A 원본': r(천명당[y], 반납률[y]),
        'B 급변 제외': r(천명당.loc[남은, y], 반납률.loc[남은, y]),
        'B 제외 시도 수': len(제외),
        'C 보정': r(보정천명당[y], 반납률[y]),
        'D 3년 평균 정류장': r(평균천명당, 반납률[y]),
        'E 스피어만': spearmanr(천명당[y], 반납률[y])[0],
        'F 한 지역 제외 최소': min(loo),
        'F 한 지역 제외 최대': max(loo),
        'p (원본)': pearsonr(천명당[y], 반납률[y])[1],
    })
표 = pd.DataFrame(행)
print('\n[2] 처리 방식별 정류장_천명당 ↔ 반납률 상관계수')
print(표.round(3).to_string(index=False))

전부음수 = (표[['A 원본', 'B 급변 제외', 'C 보정', 'D 3년 평균 정류장', 'E 스피어만', 'F 한 지역 제외 최대']] < 0).all().all()
전부기준 = (표[['A 원본', 'B 급변 제외', 'C 보정', 'D 3년 평균 정류장', 'F 한 지역 제외 최대']].abs() >= 0.4).all().all()
print('\n모든 처리 방식에서 음수:', 전부음수, '/ |r| ≥ 0.4 유지:', 전부기준)

# 3. 그래프: 연도별 처리 방식 r 막대
방식 = ['A 원본', 'B 급변 제외', 'C 보정', 'D 3년 평균 정류장', 'E 스피어만']
색 = ['#1F4E79', '#4C72B0', '#7FA6D0', '#9AA5B1', '#C9D3DD']
x = np.arange(len(연도들))
폭 = 0.16
fig, ax = plt.subplots(figsize=(11, 6))
ax.axhspan(-0.4, 0.4, color='lightgray', alpha=0.5, label='약한 상관 (|r| < 0.4)')
ax.axhline(0, color='gray', linewidth=0.8)
for i, (m, c) in enumerate(zip(방식, 색)):
    막대 = ax.bar(x + (i - 2) * 폭, 표[m], 폭, color=c, label=m)
    ax.bar_label(막대, fmt='%.2f', padding=2, fontsize=8)
for j, (_, row) in enumerate(표.iterrows()):          # 한 지역 제외 범위 (세로선)
    ax.plot([j + 2.9 * 폭, j + 2.9 * 폭], [row['F 한 지역 제외 최소'], row['F 한 지역 제외 최대']], color='black', linewidth=2)
ax.plot([], [], color='black', linewidth=2, label='F 한 지역 제외 범위')
ax.set_xticks(x, [str(y) for y in 연도들])
ax.set_ylim(-1, 0.6)
ax.set_ylabel('정류장_천명당 ↔ 반납률 상관계수 r')
ax.set_title('급변값을 어떻게 처리해도 정류장과 반납률의 음의 관계는 유지된다', fontsize=13, fontweight='bold')
ax.legend(loc='upper right', fontsize=9, ncol=2)
plt.tight_layout()
fig.savefig(f'{출력}/정류장_처리방식별_상관계수.png', dpi=150, facecolor='white')

# 4. 결과 저장
def 칸(v):
    return f'{v:.3f}' if isinstance(v, float) else str(v)


with open(f'{출력}/민감도_결과.md', 'w', encoding='utf-8') as f:
    f.write('# 회고 ② 정류장 검증 — 처리 방식별 민감도\n\n`정류장_민감도분석.py` 실행 결과\n\n')
    f.write(f'## 1. 급변 시도·연도 (전년 대비 ±10% 초과): {len(급변)}건\n\n| 연도 | 시도 | 전년 대비 |\n|---|---|---|\n')
    f.write('\n'.join(f'| {y} | {s} | {v:+.1f}% |' for s, y, v in 급변) + '\n\n')
    f.write('## 2. 처리 방식별 상관계수\n\n')
    f.write('| ' + ' | '.join(표.columns) + ' |\n|' + '---|' * len(표.columns) + '\n')
    f.write('\n'.join('| ' + ' | '.join(칸(v) for v in row) + ' |' for row in 표.itertuples(index=False)) + '\n\n')
    f.write(f'- 모든 처리 방식에서 음수: **{전부음수}**\n- 모든 처리 방식에서 |r| ≥ 0.4 유지: **{전부기준}**\n')
print(f'\n저장: {출력}/민감도_결과.md, {출력}/정류장_처리방식별_상관계수.png')
