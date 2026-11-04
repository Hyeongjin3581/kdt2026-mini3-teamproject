# [팀원 D] 정부 고령자 교통 대책 사례 분석 (Practice7 형식) - 분석 기간 2022~2024년
# 담당자:
# 출처 및 대상: 대한민국 정책브리핑 보도자료 · 정책뉴스  https://www.korea.kr
# 기사 목록 = "div.article_body div.list_type li a"
# strong(제목) , span.lead(요약) , span.source span(날짜·부처)
# 클릭이벤트 : dom.click() , .paging .num a  (정책브리핑 페이지 번호 버튼)

# [1. 주제]
# 늘어나는 고령 운전자 사고, 면허 반납을 가로막는 교통 공백
# 팀원 D 역할: 정책 확인 - 2022~2024년 정부의 고령자 교통 대책은 어떤 유형에 집중했는가 (사례 분석, 시도 결합 X)

# [2. 가설]
# 가설 1: 2022~2024년 정부의 고령자 교통 대책 중 '운전자·차량 + 면허' 대책이 '이동권·대중교통' 대책보다 많을 것이다.
# 가설 2: 이동권·대중교통 대책은 분석 기간 후반(2024년)에야 처음 등장할 것이다.
# ※ 사례 수가 적어(약 7건) 통계 검정이 아니라 사례 분석으로 판정한다. (건수 비교 + 등장 시점)

# [3. 목표]
# Playwright의 비동기 제어와 동적 페이지네이션(click)을 활용해 검색어 6개 × 보도자료·정책뉴스 목록의 모든 페이지를 순회한다.
# 기사 카드에서 제목, 요약, 날짜, 부처, 링크를 추출하여 구조화한다. (수업 참고: practice7.py)
# ※ robots.txt 확인 결과 정책브리핑은 수집 허용 (네이버 뉴스는 Disallow: / 로 수집 금지)
# ※ 검색어는 중립 단어만 쓴다. '수요응답형'(이동권 쪽), '페달'(차량 쪽)처럼 한쪽 대책 단어를 넣으면 결과가 기울어진다.

# [기본 제공 코드]
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

검색어목록 = ['고령운전자', '면허 반납', '고령자 교통안전', '어르신 교통', '노인 교통사고', '고령 보행자']
게시판목록 = [('보도자료', 'https://www.korea.kr/briefing/pressReleaseList.do'),
              ('정책뉴스', 'https://www.korea.kr/news/policyNewsList.do')]


# [수집 코드 작성 순서] - 수업 참고: practice7.py 와 같은 구조로 직접 작성한다.

# 3-1 (함수 선언): async def run() 함수를 만들고, 안에 결과를 담을 빈 리스트 item_list = [] 를 만든다.
async def run() :
    item_list = []

    # 3-2 (브라우저 실행): async with async_playwright() as p 로 Playwright 를 실행하고,
    #                    await p.chromium.launch(headless=False) 로 크로미움을 띄운 뒤 await browser.new_page() 로 빈 페이지를 연다.
    #                    (headless=False 는 창이 보이는 모드 → 처음엔 False 로 동작을 눈으로 확인하고, 잘 되면 True 로 바꿔도 된다)
    async with async_playwright() as p:
        browser = await p.chromium.launch( headless=False )
        page = await browser.new_page()

        # 3-3 (이중 반복문): for 검색어 in 검색어목록 → for 종류, 주소 in 게시판목록 으로 12번(6 × 2) 반복한다.
        for search in 검색어목록:
            for board_type, address in 게시판목록:
                # 3-4 (주소 이동): 검색어와 기간을 넣은 주소를 f-string 으로 만들어 이동한 뒤 2초 기다린다.
                #                  url 형식: {주소}?srchWord={검색어}&startDate=2022-01-01&endDate=2024-12-31&pageIndex=1
                url = f'{address}?srchWord={search}&startDate=2022-01-01&endDate=2024-12-31&pageIndex=1'

                await page.goto(url)
                await page.wait_for_timeout(2000)

                print( "\n검색어 :", search )
                print( "게시판 :", board_type )

                # 3-5 (페이지 수 세기): 페이지 번호 버튼을 가져와 len()으로 개수를 센다.
                # ※ 현재 페이지 번호까지 포함하여 전체 번호가 한 묶음에 표시되는 경우의 방식이다.
                page_buttons = await page.query_selector_all('.paging .num a')
                page_count = len(page_buttons)

                # 페이지 버튼이 없어도 현재 화면은 한 번 확인한다.
                if page_count == 0:
                    page_count = 1

                # 3-6 (페이지 버튼 클릭): 1페이지는 이미 열려 있으므로 i > 1 일 때만 버튼을 누른다.
                # ※ 순서(인덱스)가 아닌 버튼의 title 속성으로 찾는다.
                for i in range(1, page_count + 1):

                    if i > 1:
                        button = await page.query_selector(
                            f'.paging .num a[title="{i}페이지"]'
                        )
                        if button is None:
                            print( i, "페이지 버튼을 찾지 못했습니다." )
                            break
                        await button.click()
                        await page.wait_for_timeout(2000)
                    # 3-7 (기사 목록 가져오기): 기사 카드를 여러 개 가져온다.
                    # ※ 오른쪽 실시간 인기뉴스 링크가 섞이지 않도록 기사 목록 영역을 지정한다.
                    items = await page.query_selector_all(
                        'div.article_body div.list_type li a'
                    )
                    print( i, "페이지 기사 수 :", len(items) )
                    # 3-8 (요소 추출): 기사 카드마다 제목, 요약, 날짜, 부처, 링크를 꺼낸다.
                    for item in items:
                        # 제목
                        title = await item.query_selector('strong')
                        title_text = await title.inner_text() if title else '제목없음'

                        # 요약
                        summary = await item.query_selector('span.lead')
                        summary_text = await summary.inner_text() if summary else ''

                        # 날짜·부처
                        source = await item.query_selector_all('span.source span')
                        date_text = await source[0].inner_text() if len(source) > 0 else ''
                        department_text = await source[1].inner_text() if len(source) > 1 else ''

                        # 링크
                        # 확인한 게시판의 기사 링크는 /news/ 또는 /briefing/으로 시작한다.
                        link = await item.get_attribute('href')
                        link = 'https://www.korea.kr' + link if link else ''

                        print( title_text, date_text, department_text )

                        # 3-9 (데이터 적재): 검색어, 종류, 제목, 요약, 날짜, 부처, 링크를 딕셔너리로 묶어 리스트에 저장한다.
                        item_list.append({
                            '검색어': search,
                            '종류': board_type,
                            '제목': title_text.strip(),
                            '요약': summary_text.strip(),
                            '날짜': date_text.strip(),
                            '부처': department_text.strip(),
                            '링크': link
                        })

        # 3-10 (종료 · 반환): 반복이 끝나면 브라우저를 닫고 item_list를 반환한다.
        await browser.close()

    return item_list
# 3-11 (실행 · 확인): 함수를 실행하고 데이터프레임으로 바꾼 뒤 기본 정보를 확인한다.
items_list = asyncio.run(run())

df = pd.DataFrame( items_list, columns=['검색어', '종류', '제목', '요약', '날짜', '부처', '링크'] )
df.info()
print(df.head())
print( "수집된 기사 수 :", len(df) )
# 현재 실행 위치에 CSV 파일을 저장한다.
# 별도 폴더를 지정하지 않으므로 data/raw 폴더가 없어도 된다.
df.to_csv('정책브리핑_수집.csv', index=False, encoding='utf-8-sig')
print( "저장 파일 : 정책브리핑_수집.csv" )
# CSV 저장은 전체 페이지 수집과 나머지 항목 추출을 작성한 뒤 추가한다.
# df.to_csv('data/raw/정책브리핑_수집.csv', index=False, encoding='utf-8-sig')

# [4. 데이터 전처리]
# 4-1 (중복 제거): 검색어끼리 겹치는 기사를 drop_duplicates('제목') 으로 제거한다. (345 → 265건)

# 4-2 (1차 자동 필터): 정책브리핑 검색은 검색어를 단어로 쪼개서 찾아 무관 기사가 많이 섞인다.
#                     (예: '고령운전자' 검색에 환경부 홍수 대책 기사가 '고령'·'운전자' 를 따로 포함해서 걸린다)
#                     제목에 '고령|노인|어르신|면허' 가 있고, 제목+요약에 '운전|교통|보행|이동|버스|면허' 가 있는 기사만 남긴다.
#                     df[ df['제목'].str.contains('고령|노인|어르신|면허') & (df['제목'] + ' ' + df['요약']).str.contains('운전|교통|보행|이동|버스|면허') ]
#                     → 22건 (수업 참고: day08/Practice3.py 문제 3 & 연산자)

# 4-3 (본문 수집): 정책뉴스는 3-2 ~ 3-4 와 같은 방식으로 브라우저를 열고 링크마다 await 페이지.goto(링크) 한 뒤
#                  본문 = await 페이지.query_selector('div.view_cont') → await 본문.inner_text() 로 본문을 모은다.
#                  ※ 보도자료는 본문이 대부분 첨부파일(hwpx/pdf)에만 있어 제목+요약으로 분류한다.

# 4-4 (2차 수작업 분류): 결과를 to_csv 로 저장해 엑셀에서 열고, '대책유형' 열에 아래 기준표의 이름 또는 '제외' 를 적는다.
#   ① 운전자·차량: 페달 오조작 방지 장치, 첨단 안전장치 등
#   ② 면허·적성: 조건부 면허, 적성검사, 면허 자진반납 제도
#   ③ 보행 환경: 노인 보행자 사고 다발지점 정비, 보호구역 등
#   ④ 이동권·대중교통: 수요응답형 버스, 대중교통 확충, 교통카드 등
#   ⑤ 기타: 사고 분석·조사 등
#   제외: 통계 발표(예: 고령자 통계), 복지·주거·인구정책 일반, 단어만 겹치는 기사
#   ※ 기준표를 먼저 정하고 분류한다. 애매한 사례는 다른 팀원 1명과 교차 확인하고 이유를 적는다.

# 4-5 (사례 묶기): 같은 날·같은 부처의 보도자료와 정책뉴스는 같은 대책이므로 1개 사례로 묶는다. (이중 집계 방지)
#                  (힌트: '제외' 를 뺀 뒤 drop_duplicates(['날짜', '부처', '대책유형']) ) → 최종 약 7건

# 4-6 (형변환 - 날짜): pd.to_datetime 으로 날짜를 객체화하고 .dt.year 로 '연도' 열을 만든다. (수업 참고: day08/p-02.py 9번)

# 4-7 (결측치 처리): 요약이 비어 있는 보도자료는 제목만으로 분류하고 그 사실을 기록한다. (임의로 채우지 않는다)

# 4-8 (저장): 사례번호, 날짜, 연도, 부처, 제목, 대책유형, 종류, 링크 컬럼을 data/clean/정제_D_정책.csv 로 저장한다.


# [5. 데이터 시각화 및 분석]
# 5-1 (가설 2 - 대책 타임라인): plt.scatter(x=날짜, y=대책유형) 으로 사례 1건을 점 1개로 그린다.
#                              (수업 참고: day09/g-01.py 3번 산점도) → 이동권·대중교통 점이 2024년에 처음 나오면 가설 2 채택

# 5-2 (가설 1 - 유형별 사례 수): value_counts() 로 대책유형별 사례 수를 구해 막대 그래프 + bar_label 로 그린다.
#                               (수업 참고: day09/g-01.py 2번 막대 차트 + bar_label)
#                               → (운전자·차량 + 면허·적성) > 이동권·대중교통 이면 가설 1 채택

# 5-3 (보조 분석): value_counts() 로 부처별 사례 수를 확인한다. (어느 부처가 고령자 교통 대책을 주로 발표하는가)

# 5-4 (인사이트 정리): 각 그래프 아래에 "그래서 무엇을 발견했는가?" 를 한 줄로 적는다.
#                     ※ 사례 수가 적으므로 "경향 수준으로 해석한다" 는 한계를 함께 적는다.


# [6. 보고서 기록용 (데이터 리터러시)]
# 6-1 (단계별 건수): 수집 345 → 제목 중복 제거 265 → 자동 필터 22 → 수작업 분류 → 사례 묶기 후 건수
# 6-2 (방법을 바꾼 이유): 처음 계획한 키워드 빈도 분석은 검색이 단어를 쪼개 무관 기사가 대부분이고,
#                        정책뉴스 본문에서 '고령 운전자·면허 반납' 을 직접 언급한 기사가 표본 50건 중 0건이라 사례 분석으로 바꿨다.
# 6-3 (분류 기준): 4-4 기준표와 제외 예시, 애매했던 사례와 결정 이유를 적는다.
# 6-4 (기술적 트러블슈팅 예시): Practice7 처럼 페이지 버튼을 순서(인덱스)로 누르자 IndexError(list index out of range)가 발생했다
#                              → 버튼의 title("2페이지")로 찾아 누르도록 바꿔 345건을 모두 수집했다.
#                              또, 처음에 requests + get_text(' ') 로 받았을 때는 검색어 강조 표시 앞뒤에 띄어쓰기가 끼어
#                              "고령 자 통계" 처럼 제목이 바뀌어 중복이 덜 걸러졌다 → inner_text() 는 화면에 보이는 그대로 가져와 해결.
# 6-5 (수집처 · 검색어 선택 이유): 네이버 robots.txt Disallow: / → 정책브리핑 / 한쪽 대책 단어는 검색어에서 제외