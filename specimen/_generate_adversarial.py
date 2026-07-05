"""
_generate_adversarial.py
========================
기존 specimen이 커버하지 못하는 adversarial edge case를 생성.
기존 24개에 추가로 12+ 개의 고난도 specimen 생성.

Edge cases:
  11. 헤더 없는 순수 숫자 데이터
  12. 10행짜리 깊은 다중 헤더
  13. 피벗 테이블 (행/열 모두 헤더)
  14. 한 시트에 3개 표 (큰 간격)
  15. 소계/합계가 데이터 중간에 산재
  16. 극단적 sparse (5% 미만 fill)
  17. 행/열 헤더가 모두 있는 크로스탭
  18. 완전 빈 열이 중간에 있는 테이블
  19. 타이틀 3행 + 부제목 + 범례 + 데이터 + 각주 5행
  20. 한글/영문/숫자 혼합 헤더 + 단위행
  21. 열 개수가 행마다 다른 극단적 ragged
  22. 단일 열 데이터 (1열짜리 표)
"""

import csv
import random
import os
from pathlib import Path

SPECIMEN_DIR = Path(__file__).resolve().parent
random.seed(42)


def write_csv(name: str, rows: list[list], delimiter: str = ","):
    path = SPECIMEN_DIR / name
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=delimiter)
        w.writerows(rows)
    print(f"  ✓ {name} ({len(rows)} rows)")


# ──────────────────────────────────────────
# 11. No-header pure numeric data
# ──────────────────────────────────────────
def gen_11():
    rows = []
    for _ in range(100):
        rows.append([round(random.gauss(50, 15), 2) for _ in range(6)])
    write_csv("11_no_header_numeric.csv", rows)


# ──────────────────────────────────────────
# 12. Deep multi-header (10 header rows)
# ──────────────────────────────────────────
def gen_12():
    rows = []
    rows.append(["", "", "2024년 상반기 실적 보고서", "", "", "", "", ""])
    rows.append(["", "", "작성부서: 경영기획팀", "", "", "", "", ""])
    rows.append(["", "", "보고일: 2024-06-30", "", "", "", "", ""])
    rows.append([""])
    rows.append(["", "매출", "매출", "매출", "비용", "비용", "비용", "이익"])
    rows.append(["분류", "제품A", "제품B", "제품C", "인건비", "재료비", "기타", "순이익"])
    rows.append(["단위", "백만원", "백만원", "백만원", "백만원", "백만원", "백만원", "백만원"])
    rows.append([""])
    # Actual column names at row 5 (0-indexed), data starts at row 8
    for month in ["1월", "2월", "3월", "4월", "5월", "6월"]:
        rows.append([month,
                     random.randint(100, 500), random.randint(80, 400),
                     random.randint(50, 300), random.randint(30, 200),
                     random.randint(20, 150), random.randint(10, 50),
                     ""])
    rows.append([""])
    rows.append(["합계", 1800, 1500, 1000, 600, 400, 150, 1150])
    rows.append(["※ 잠정치이며 감사 후 변경될 수 있음", "", "", "", "", "", "", ""])
    rows.append(["자료: 경영기획팀 내부 자료", "", "", "", "", "", "", ""])
    write_csv("12_deep_multiheader.csv", rows)


# ──────────────────────────────────────────
# 13. Pivot table (row + column headers)
# ──────────────────────────────────────────
def gen_13():
    regions = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종"]
    products = ["전자", "식품", "의류", "화학", "기계"]
    rows = []
    rows.append(["지역/제품"] + products + ["합계"])
    for region in regions:
        vals = [random.randint(10, 99) for _ in products]
        rows.append([region] + vals + [sum(vals)])
    # 소계 행
    totals = ["합계"] + [sum(rows[i+1][j+1] for i in range(len(regions)))
                        for j in range(len(products))]
    totals.append(sum(totals[1:]))
    rows.append(totals)
    write_csv("13_pivot_crosstab.csv", rows)


# ──────────────────────────────────────────
# 14. 3 tables on one sheet (big gaps)
# ──────────────────────────────────────────
def gen_14():
    rows = []

    # Table 1: 직원 목록
    rows.append(["직원번호", "이름", "부서", "입사일"])
    for i in range(1, 11):
        rows.append([f"EMP{i:03d}", f"직원{i}", random.choice(["영업", "개발", "인사"]),
                     f"2020-{random.randint(1,12):02d}-{random.randint(1,28):02d}"])

    # 5줄 빈 행
    for _ in range(5):
        rows.append([])

    # Table 2: 매출 데이터
    rows.append(["월", "매출액", "비용", "이익"])
    for m in range(1, 7):
        rev = random.randint(1000, 5000)
        cost = random.randint(500, 3000)
        rows.append([f"{m}월", rev, cost, rev - cost])

    # 8줄 빈 행 + 주석
    for _ in range(5):
        rows.append([])
    rows.append(["아래는 부서별 예산입니다", "", ""])
    rows.append([])
    rows.append([])

    # Table 3: 부서별 예산
    rows.append(["부서", "배정예산", "집행액", "잔액", "집행률"])
    for dept in ["영업", "개발", "인사", "총무", "마케팅"]:
        budget = random.randint(5000, 20000)
        spent = random.randint(2000, budget)
        rows.append([dept, budget, spent, budget - spent, f"{spent/budget*100:.1f}%"])

    write_csv("14_three_tables_gapped.csv", rows)


# ──────────────────────────────────────────
# 15. Subtotals interspersed in data
# ──────────────────────────────────────────
def gen_15():
    rows = []
    rows.append(["구분", "항목", "1분기", "2분기", "3분기", "4분기", "연간"])
    categories = {"인건비": ["급여", "상여", "퇴직금", "4대보험"],
                  "재료비": ["원자재", "부자재", "포장재"],
                  "경비": ["임차료", "수도광열", "통신비", "소모품", "여비교통"]}

    for cat, items in categories.items():
        cat_totals = [0, 0, 0, 0]
        for item in items:
            vals = [random.randint(100, 999) for _ in range(4)]
            cat_totals = [a + b for a, b in zip(cat_totals, vals)]
            rows.append(["", item] + vals + [sum(vals)])
        rows.append([f"소계({cat})", "", *cat_totals, sum(cat_totals)])

    # 총합계
    grand = [0] * 4
    for row in rows[1:]:
        if row[0] == "" and len(row) >= 6:
            for j in range(4):
                grand[j] += row[j + 2] if isinstance(row[j + 2], int) else 0
    rows.append(["총합계", "", *grand, sum(grand)])
    rows.append([])
    rows.append(["※ 단위: 만원", "", "", "", "", "", ""])
    write_csv("15_subtotals_interspersed.csv", rows)


# ──────────────────────────────────────────
# 16. Extremely sparse (< 5% fill)
# ──────────────────────────────────────────
def gen_16():
    rows = []
    headers = [f"Sensor_{i}" for i in range(30)]
    rows.append(["Timestamp"] + headers)
    for h in range(200):
        row = [f"2024-01-01 {h // 60:02d}:{h % 60:02d}:00"]
        for _ in range(30):
            # Only 3% of cells have data
            if random.random() < 0.03:
                row.append(round(random.uniform(0, 100), 2))
            else:
                row.append("")
        rows.append(row)
    write_csv("16_extreme_sparse.csv", rows)


# ──────────────────────────────────────────
# 17. Cross-tab with row headers
# ──────────────────────────────────────────
def gen_17():
    rows = []
    years = ["2020", "2021", "2022", "2023", "2024"]
    rows.append(["", ""] + years)
    rows.append(["대분류", "중분류"] + ["매출(억)" for _ in years])

    categories = {
        "전자": ["TV", "냉장고", "세탁기", "에어컨"],
        "생활": ["식품", "음료", "세제"],
        "패션": ["의류", "신발", "액세서리"],
    }
    for major, minors in categories.items():
        for i, minor in enumerate(minors):
            row = [major if i == 0 else "", minor]
            row += [random.randint(10, 200) for _ in years]
            rows.append(row)

    write_csv("17_crosstab_rowheaders.csv", rows)


# ──────────────────────────────────────────
# 18. Empty columns in the middle
# ──────────────────────────────────────────
def gen_18():
    rows = []
    rows.append(["ID", "Name", "", "Score", "", "Grade", "Comment"])
    for i in range(50):
        rows.append([i + 1, f"Student_{i+1}", "",
                     random.randint(40, 100), "",
                     random.choice(["A", "B", "C", "D", "F"]),
                     random.choice(["", "재시험", "우수", ""])])
    write_csv("18_empty_cols_middle.csv", rows)


# ──────────────────────────────────────────
# 19. Title + subtitle + legend + data + 5 footnotes
# ──────────────────────────────────────────
def gen_19():
    rows = []
    rows.append(["2024년 국민건강영양조사 결과"])
    rows.append(["- 질병관리청 만성질환관리국 -"])
    rows.append(["조사기간: 2024.01 ~ 2024.12"])
    rows.append(["범례: M=남성, F=여성, T=전체"])
    rows.append([])
    rows.append(["연령대", "BMI_M", "BMI_F", "BMI_T", "혈압_M", "혈압_F", "혈압_T"])
    for age in ["20대", "30대", "40대", "50대", "60대", "70대", "80+세"]:
        row = [age]
        for _ in range(6):
            row.append(round(random.uniform(18, 32), 1))
        rows.append(row)
    rows.append([])
    rows.append(["주1) BMI = 체질량지수(kg/m²)"])
    rows.append(["주2) 혈압 = 수축기혈압(mmHg) 평균"])
    rows.append(["주3) 결측치는 보정 후 분석"])
    rows.append(["자료: 질병관리청 국민건강영양조사 제9기"])
    rows.append(["작성일: 2025-03-15"])
    write_csv("19_title_footnotes_heavy.csv", rows)


# ──────────────────────────────────────────
# 20. Mixed-language headers + unit row
# ──────────────────────────────────────────
def gen_20():
    rows = []
    rows.append(["Product ID", "제품명", "Category", "가격(Price)", "재고수량(Stock)", "Rating"])
    rows.append(["(텍스트)", "(한글)", "(영문)", "(KRW/원)", "(개/EA)", "(1~5)"])
    for i in range(80):
        rows.append([
            f"P{i+1:04d}",
            f"제품_{i+1}",
            random.choice(["Electronics", "Food", "Fashion", "전자", "식품"]),
            random.randint(1000, 99000),
            random.randint(0, 500),
            round(random.uniform(1, 5), 1),
        ])
    write_csv("20_mixed_lang_units.csv", rows)


# ──────────────────────────────────────────
# 21. Extreme ragged (column count varies wildly)
# ──────────────────────────────────────────
def gen_21():
    rows = []
    rows.append(["Key", "Value1", "Value2", "Value3", "Value4", "Extra1", "Extra2", "Extra3"])
    for i in range(60):
        ncols = random.randint(2, 8)
        row = [f"K{i+1:03d}"] + [random.randint(1, 100) for _ in range(ncols - 1)]
        rows.append(row)
    write_csv("21_extreme_ragged.csv", rows)


# ──────────────────────────────────────────
# 22. Single-column data
# ──────────────────────────────────────────
def gen_22():
    rows = [["Measurements"]]
    for _ in range(150):
        rows.append([round(random.gauss(100, 25), 3)])
    write_csv("22_single_column.csv", rows)


def main():
    print(f"\n{'═' * 60}")
    print(f"  Generating Adversarial Specimens")
    print(f"{'═' * 60}\n")

    generators = [
        gen_11, gen_12, gen_13, gen_14, gen_15, gen_16,
        gen_17, gen_18, gen_19, gen_20, gen_21, gen_22,
    ]
    for gen in generators:
        try:
            gen()
        except Exception as e:
            print(f"  ✗ {gen.__name__}: {e}")

    print(f"\n  Generated {len(generators)} adversarial specimens")


if __name__ == "__main__":
    main()
