# [개인 보완] 발표 직전 추가한 그래프 (팀 결과물 이후 개인 작업)
# 실행: 저장소 최상위에서 python "개선/00_발표자료_보완/융합_상관계수_그래프.py" data "개선/00_발표자료_보완"

import sys
import numpy as np
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

m = pd.read_csv(f'{DATA}/merge/결합테이블.csv')
연도들 = [2022, 2023, 2024]
행 = []
for y in 연도들:
    t = m[m['연도'] == y]
    행.append({'연도': y,
              '정류장': t['정류장_천명당'].corr(t['반납률']),
              '고령화율': t['고령화율'].corr(t['반납률']),
              'A3': t['반납률'].corr(t['고령사고_만명당'])})
표 = pd.DataFrame(행)
print(표.round(3))

계열 = [('정류장', '정류장_천명당 ↔ 반납률 (핵심 가설)', '#1F4E79'),
      ('고령화율', '고령화율 ↔ 반납률 (비교 기준)', '#9AA5B1'),
      ('A3', '반납률 ↔ 고령사고 (A-3)', '#DD8452')]


def 그리기(사용, 파일명, 제목):
    x = np.arange(len(연도들))
    폭 = 0.8 / len(사용)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.axhspan(-0.4, 0.4, color='lightgray', alpha=0.5, label='약한 상관 (|r| < 0.4)')
    ax.axhline(0, color='gray', linewidth=0.8)
    for i, (col, 라벨, 색) in enumerate(사용):
        위치 = x + (i - (len(사용) - 1) / 2) * 폭
        막대 = ax.bar(위치, 표[col], 폭, color=색, label=라벨)
        ax.bar_label(막대, fmt='%.2f', padding=3, fontsize=11)
    ax.set_xticks(x, [str(y) for y in 연도들])
    ax.set_ylim(-1, 1)
    ax.set_ylabel('상관계수 r')
    ax.set_title(제목, fontsize=13, fontweight='bold')
    ax.legend(loc='upper right', fontsize=10)
    plt.tight_layout()
    fig.savefig(f'{OUT}/{파일명}', dpi=150, facecolor='white')
    plt.close(fig)


그리기(계열, '융합_정류장_고령화율_A3_상관계수.png', '연도별 상관계수: 핵심 가설 · A-3')
그리기([계열[0], 계열[2]], '융합_정류장_A3_상관계수.png', '연도별 상관계수: 정류장 · A-3')
