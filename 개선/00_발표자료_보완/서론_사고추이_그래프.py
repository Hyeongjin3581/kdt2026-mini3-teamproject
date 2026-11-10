# [개인 보완] 발표 직전 추가한 그래프 (팀 결과물 이후 개인 작업)
# 실행: 저장소 최상위에서 python "개선/00_발표자료_보완/서론_사고추이_그래프.py" data "개선/00_발표자료_보완"

import sys
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

DATA = sys.argv[1]   # MINI3/data
OUT = sys.argv[2]    # MINI3/data/graphs

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

a = pd.read_csv(f'{DATA}/정제_A_사고.csv')
b = pd.read_csv(f'{DATA}/정제_B_반납인구.csv')
전국 = b.groupby('연도')[['65세이상인구', '반납건수']].sum()
전국['반납률'] = 전국['반납건수'] / 전국['65세이상인구'] * 1000
전국['고령사고건수'] = a.groupby('연도')['고령사고건수'].sum()
누적 = (전국.loc[2024] / 전국.loc[2022] - 1) * 100
연도라벨 = [str(y) for y in 전국.index]

항목목록 = [('고령사고건수', '고령운전자 사고', '#55A868', '{:,.0f}'),
          ('65세이상인구', '65세 이상 인구', '#4C72B0', '{:,.0f}'),
          ('반납건수', '면허 반납 건수', '#DD8452', '{:,.0f}'),
          ('반납률', '반납률', '#C44E52', '{:.2f}')]


def 패널(ax, col, 제목, 색, 형식):
    값 = 전국[col]
    막대 = ax.bar(연도라벨, 값.values, color=색, width=0.6)
    ax.bar_label(막대, labels=[형식.format(v) for v in 값.values], padding=3, fontsize=11)
    ax.set_title(f'{제목} ({누적[col]:+.1f}%)', fontsize=12)
    ax.set_ylim(0, 값.max() * 1.15)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p, f=형식: f.format(x)))
    ax.grid(axis='x', visible=False)


# ① 사고 단독
fig, ax = plt.subplots(figsize=(5.5, 5.5))
패널(ax, *항목목록[0])
fig.suptitle('2022~2024년 고령운전자 사고', fontsize=14, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{OUT}/서론_고령운전자사고_추이.png', dpi=150, facecolor='white')
plt.close(fig)

# ② 기존 3패널 + 사고 = 4패널
fig, axes = plt.subplots(1, 4, figsize=(20, 5.5))
for ax, 항목 in zip(axes, 항목목록):
    패널(ax, *항목)
fig.suptitle('2022~2024년 고령운전자 사고 · 고령 인구 · 반납 건수 · 반납률', fontsize=14, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{OUT}/서론_사고_인구_반납_4패널.png', dpi=150, facecolor='white')
plt.close(fig)

# ③ 슬라이드용 2×2 배치 (같은 4패널)
fig, axes = plt.subplots(2, 2, figsize=(11, 8))
for ax, 항목 in zip(axes.flat, 항목목록):
    패널(ax, *항목)
fig.suptitle('2022~2024년 고령운전자 사고 · 고령 인구 · 반납 건수 · 반납률', fontsize=14, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{OUT}/서론_사고_인구_반납_4패널_2x2.png', dpi=150, facecolor='white')
plt.close(fig)

print(전국.round(2))
print(누적.round(2).to_dict())
