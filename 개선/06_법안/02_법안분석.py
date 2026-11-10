# [개인 보완] 회고 ① C안 (2) 고령운전자 관련 법안 고르기 → 유형·시기·처리 결과 분석
# 실행: 저장소 최상위에서 python "개선/06_법안/02_법안분석.py"
#
# 1) 관련 법안: 제안이유에 고령 표현(고령·65/70/75세·노인·어르신)과 운전·면허 표현이 함께 있는 법안
# 2) 유형: 정책브리핑(A안)과 같은 기준표 ① 운전자·차량 ② 면허·적성 ③ 보행 환경 ④ 이동권·대중교통 ⑤ 기타
# 3) 결과: 대수·연도별 발의 수, 유형 분포, 처리 결과(가결·대안반영·폐기·계류)

import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

출력 = '개선/06_법안'
d = pd.read_csv(f'{출력}/법안_원자료.csv', dtype=str).fillna('')
d['연도'] = d['PROPOSE_DT'].str[:4]

# 검수 후 기준을 좁혔다: '어린이·노인 및 장애인'처럼 단어만 겹치는 법안(어린이보호구역, 학원 강사 나이 제한, PM 주차 등)이 섞였기 때문
#   (가) 고령운전자 법안: 제안이유에 고령운전자를 직접 가리키는 표현이 있는 경우
#   (나) 노인 보행 법안: '노인 보호구역'을 다루고, 본문에서 노인이 어린이보다 더 많이(같거나) 언급되는 경우
고령운전자표현 = r'고령\s?운전|노인\s?운전|어르신\s?운전|(65|70|75)세\s?이상[^.]{0,20}(운전|면허)|자진\s?반납'
노인보호 = r'노인\s?(및\s?장애인\s?)?보호\s?구역'
d['고령운전자법안'] = d['SUMMARY'].str.contains(고령운전자표현)
d['노인보행법안'] = d['SUMMARY'].str.contains(노인보호) & (d['SUMMARY'].str.count('노인') >= d['SUMMARY'].str.count('어린이'))
d['관련'] = d['고령운전자법안'] | d['노인보행법안']

사전 = {
    '① 운전자·차량': r'페달|오조작|첨단\s?안전|안전\s?장치|자동\s?제동|고령\s?운전자\s?표지|표지\s?부착',
    '② 면허·적성': r'적성\s?검사|갱신|조건부|인지\s?(기능|능력)|자진\s?반납|면허\s?(를|증)?\s?반납|운전\s?능력\s?(평가|검사)|교통\s?안전\s?교육',
    '③ 보행 환경': r'노인\s?보호\s?구역|보행|횡단',
    '④ 이동권·대중교통': r'대중교통|교통\s?카드|이동\s?(권|지원|수단)|수요\s?응답|교통비',
}
for 유형, 패턴 in 사전.items():
    d[유형] = d['SUMMARY'].str.count(패턴)
유형열 = list(사전)
d['주유형'] = np.where(d[유형열].max(axis=1) >= 1, d[유형열].idxmax(axis=1), '⑤ 기타')
d['처리'] = np.select([d['PROC_RESULT'].str.contains('가결'), d['PROC_RESULT'].str.contains('대안반영|수정안반영'),
                     d['PROC_RESULT'].str.contains('폐기|철회|부결'), d['PROC_RESULT'] == ''],
                    ['가결', '대안반영', '폐기·철회', '계류(처리 전)'], d['PROC_RESULT'])

관련 = d[d['관련']].copy()
print('전체 법안:', len(d), '/ 관련:', len(관련), '(고령운전자', int(관련['고령운전자법안'].sum()), '· 노인 보행만', int((관련['노인보행법안'] & ~관련['고령운전자법안']).sum()), ')')
print('\n대수별:', 관련['AGE'].value_counts().sort_index().to_dict())
print('연도별:', 관련['연도'].value_counts().sort_index().to_dict())
print('주 유형:', 관련['주유형'].value_counts().to_dict())
print('처리 결과:', 관련['처리'].value_counts().to_dict())
교차 = pd.crosstab(관련['주유형'], 관련['처리'])
print('\n유형 × 처리 결과')
print(교차.to_string())

관련[['AGE', 'BILL_NO', 'BILL_NAME', 'PROPOSER', 'PROPOSE_DT', 'PROC_RESULT', '처리', '주유형', 'SUMMARY']] \
    .to_csv(f'{출력}/고령운전자_법안목록.csv', index=False, encoding='utf-8-sig')

# 그래프: 연도별 발의 수 (유형 누적) + 처리 결과
표 = 관련.pivot_table(index='연도', columns='주유형', values='BILL_NO', aggfunc='count', fill_value=0).sort_index()
색 = {'① 운전자·차량': '#4C72B0', '② 면허·적성': '#55A868', '③ 보행 환경': '#DD8452', '④ 이동권·대중교통': '#C44E52', '⑤ 기타': '#9AA5B1'}
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={'width_ratios': [2.2, 1]})
아래 = np.zeros(len(표))
for 유형 in [c for c in 색 if c in 표.columns]:
    ax1.bar(표.index, 표[유형], bottom=아래, color=색[유형], label=유형, zorder=3)
    아래 += 표[유형].values
for x, v in zip(표.index, 아래):
    ax1.text(x, v + 0.3, f'{int(v)}', ha='center', fontsize=10)
ax1.set_title(f'고령운전자 관련 법률안 발의 수 (20~22대 국회, {len(관련)}건)', fontsize=12, fontweight='bold')
ax1.set_ylabel('발의 건수')
ax1.legend(fontsize=9)
처리 = 관련['처리'].value_counts()
ax2.barh(처리.index[::-1], 처리.values[::-1], color='#1F4E79', zorder=3)
for y, v in enumerate(처리.values[::-1]):
    ax2.text(v + 0.3, y, f'{v}건', va='center', fontsize=10)
ax2.set_title('처리 결과', fontsize=12, fontweight='bold')
plt.tight_layout()
fig.savefig(f'{출력}/법안_연도별_유형_처리.png', dpi=150, facecolor='white')
print(f'\n저장: {출력}/고령운전자_법안목록.csv, 법안_연도별_유형_처리.png')
