# [기본 제공 코드]
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False
sns.set_theme(font='Malgun Gothic', rc={'axes.unicode_minus': False}, style='whitegrid')

# 불러오기
정류장22 = pd.read_csv('./data/한국교통안전공단_전국 대중교통 버스정류장 현황_20221231.csv', encoding='cp949')
정류장23 = pd.read_csv('./data/한국교통안전공단_전국 대중교통 버스정류장 현황_20231231.csv', encoding='cp949')
정류장24 = pd.read_csv('./data/한국교통안전공단_전국 대중교통 버스정류장 현황_20241231.csv', encoding='cp949')
정류장22.info()
정류장23.info()
정류장24.info()

# 연도 열 넣고 세로로 합치기
정류장22['연도'] = 2022
정류장23['연도'] = 2023
정류장24['연도'] = 2024
df = pd.concat([정류장22, 정류장23, 정류장24], ignore_index=True)
print(df.shape)

# 정류장24.info()   ← 컬럼과 행 수를 한 번 더 확인한다
정류장22.info() 
정류장23.info() 
정류장24.info() 

# 형변환
print(df.dtypes)    # 변환 전
for col in ['전체버스정류장', '유개버스정류장']:
    df[col] = pd.to_numeric(df[col].astype(str).str.strip(), errors='coerce')
print(df.dtypes)    # 변환 후
# → 기록: 컬럼 정의서상 문자형이고 2022년 원본은 숫자 뒤에 공백이 있어서, 공백을 지우고 숫자형으로 확정했다. 변환 후 int64

# 결측치 확인
print(df.isnull().sum())
# 기록: isnull().sum() 확인 결과 0건 (errors='coerce'로 바꾸다 실패한 값도 없음)

# 시도명 통일
시도매핑 = {'서울': '서울특별시', '부산': '부산광역시', '대구': '대구광역시', '인천': '인천광역시',
         '광주': '광주광역시', '대전': '대전광역시', '울산': '울산광역시', '세종': '세종특별자치시',
         '경기': '경기도', '강원': '강원특별자치도', '충북': '충청북도', '충남': '충청남도',
         '전북': '전북특별자치도', '전남': '전라남도', '경북': '경상북도', '경남': '경상남도',
         '제주': '제주특별자치도'}
df['시도명'] = df['구분'].str.strip().replace(시도매핑)
print(df['시도명'].nunique())
# 기록: 매핑 안 된 시도 없음, 17개

# 유개비율
df['유개비율'] = df['유개버스정류장'] / df['전체버스정류장'] * 100
# 기록: 34.4% ~ 93.7%

# 정류장 천명당 (B파일 필요)
import os

B경로 = './data/정제_B_반납인구.csv'

if os.path.exists(B경로):
    B = pd.read_csv(B경로, encoding='utf-8-sig')
    df = df.merge(B[['연도', '시도명', '65세이상인구']], on=['연도', '시도명'], how='left')
    print(df['65세이상인구'].isnull().sum())    # 0이어야 함
    df['정류장_천명당'] = df['전체버스정류장'] / df['65세이상인구'] * 1000
else:
    print('B 파일 없음 → 건너뜀')
    df['정류장_천명당'] = np.nan

# 전년대비 ±10% 급변 확인
df = df.sort_values(['시도명', '연도'])
df['전년대비_%'] = df.groupby('시도명')['전체버스정류장'].pct_change() * 100
print(df[df['전년대비_%'].abs() > 10][['연도', '시도명', '전년대비_%']])
# 기록: 2023년 충북 +21.6 · 대전 −15.1 · 세종 +13.6 · 경북 −12.6 · 경남 +12.0 · 전남 +11.1
# 2024년 대전 +19.2 · 인천 −14.2 · 세종 +10.2 → 조사·집계 기준이 바뀌었을 가능성

# 저장
정제 = df[['연도', '시도명', '전체버스정류장', '유개버스정류장', '유개비율', '정류장_천명당']]
print(정제.shape)   # (51, 6)
정제.to_csv('./data/정제_C_정류장.csv', index=False, encoding='utf-8-sig')


# 여기부터 반납률 때문에 B 파일 있어야 함
# 가설 1: 시도별 막대그래프
plt.figure(figsize=(9, 10))
sns.barplot(data=df, x='정류장_천명당', y='시도명', hue='연도')
plt.title('시도별 고령 인구 천 명당 버스정류장 수')
plt.show()

for 연도 in [2022, 2023, 2024]:
    s = df[df['연도'] == 연도]['정류장_천명당']
    배수 = s.max() / s.min()
    print(연도, round(배수, 2), '배', '→ 채택' if 배수 >= 2 else '→ 기각')
# 판정: 2배이상이면 채택

# 가설 2: 정류장 vs 반납률 산점도
df = df.merge(B[['연도', '시도명', '반납률']], on=['연도', '시도명'], how='left')

plt.figure(figsize=(8, 6))
sns.scatterplot(data=df, x='정류장_천명당', y='반납률', hue='연도')
plt.title('정류장 수와 면허 반납률')
plt.show()

for 연도 in [2022, 2023, 2024]:
    r = df[df['연도'] == 연도][['정류장_천명당', '반납률']].corr().iloc[0, 1]
    print(연도, 'r =', round(r, 3), '→ 채택' if r >= 0.4 else '→ 기각')
# 판정: 3개 연도 모두 0.4 이상이면 채택

# 가설 3: 유개비율 vs 반납률
plt.figure(figsize=(8, 6))
sns.scatterplot(data=df, x='유개비율', y='반납률', hue='연도')
plt.title('유개정류장 비율과 면허 반납률')
plt.show()

for 연도 in [2022, 2023, 2024]:
    r = df[df['연도'] == 연도][['유개비율', '반납률']].corr().iloc[0, 1]
    print(연도, 'r =', round(r, 3), '→ 채택' if r >= 0.4 else '→ 기각')

# 인사이트 정리
# 5-1 발견: ○○가 가장 많고 ○○가 가장 적어 약 ○배 차이 → 가설 1 채택
# 5-2 발견: r = ○○ → 정류장이 많은 시도일수록 반납률이 (높은/낮은) 경향
# 5-3 발견: r = ○○ → 정류장의 '질'은 반납률과 (관련 있음/없음)