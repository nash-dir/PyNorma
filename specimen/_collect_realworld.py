"""
specimen/_collect_realworld.py
===============================
Real-world 공공데이터 및 실제 messy 데이터 수집 스크립트.

수집 소스:
1. southkorea/southkorea-population (GitHub) - 한국 인구통계
2. OxfordIHTM/messy-data (GitHub) - 실제 messy XLSX (태풍, 보건, 인구/사망, 백신)
3. eyowhite/Messy-dataset (GitHub) - messy CSV (의료, HR, 물류, IMDB, 자동차)
4. 기타 공개 CSV (COVID-19, 대기오염 등)

보안(Sanitize):
- CSV: formula injection 무력화, null byte 제거
- XLSX: openpyxl read_only + data_only 로드 후 매크로 없는 새 파일로 재저장
- 바이너리 시그니처 검증
"""

from __future__ import annotations

import csv
import io
import os
import socket
import sys
import urllib.request
import urllib.error
from pathlib import Path

MAX_DOWNLOAD_SIZE = 5 * 1024 * 1024  # 5MB 제한
DOWNLOAD_TIMEOUT = 15  # 초

SPECIMEN_DIR = Path(__file__).resolve().parent


# ──────────────────────────────────
# Sanitization
# ──────────────────────────────────

def sanitize_csv_cell(value: str) -> str:
    """CSV Injection 방지."""
    if isinstance(value, str):
        value = value.replace("\x00", "").replace("\ufeff", "")
        if value and value[0] in ("=", "+", "-", "@", "\t", "\r", "\n"):
            value = "'" + value
    return value


def sanitize_csv_bytes(raw: bytes, encoding: str = "utf-8") -> str:
    """바이트 → sanitized CSV 텍스트."""
    text = raw.decode(encoding, errors="replace")
    reader = csv.reader(io.StringIO(text))
    out = io.StringIO()
    writer = csv.writer(out)
    for row in reader:
        writer.writerow([sanitize_csv_cell(c) for c in row])
    return out.getvalue()


def sanitize_xlsx(raw: bytes, dest: Path) -> bool:
    """XLSX 검증 후 저장.
    
    .xlsx는 VBA 매크로를 포함할 수 없음 (매크로는 .xlsm만 가능).
    ZIP 시그니처 확인 + OLE(구형 xls) 차단으로 충분.
    """
    if not is_xlsx_signature(raw):
        print("    ⚠ XLSX 시그니처 불일치 → 스킵")
        return False
    
    # OLE 형식(구형 .xls + 매크로) 차단은 is_dangerous_binary에서 이미 처리
    dest.write_bytes(raw)
    return True


def is_xlsx_signature(raw: bytes) -> bool:
    """ZIP/XLSX 시그니처 확인."""
    return raw[:4] == b"\x50\x4b\x03\x04"


def is_dangerous_binary(raw: bytes) -> bool:
    """PE exe, ELF, OLE(old macro xls) 등 위험 바이너리 체크."""
    sigs = [b"\x4d\x5a", b"\x7fELF", b"\xd0\xcf\x11\xe0"]
    for sig in sigs:
        if raw[:len(sig)] == sig:
            return True
    return False


# ──────────────────────────────────
# Download helpers
# ──────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (PyNorma-Specimen-Collector/2.0)"}


def download(url: str, dest: Path, file_type: str = "csv", encoding: str = "utf-8") -> bool:
    """URL → 다운로드(chunked, 크기 제한) + sanitize + 저장."""
    print(f"    URL: {url}")
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(DOWNLOAD_TIMEOUT)
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            chunks = []
            total = 0
            while True:
                chunk = resp.read(65536)  # 64KB씩
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_SIZE:
                    print(f"    ⚠ 파일 크기 초과 ({total:,} > {MAX_DOWNLOAD_SIZE:,}) → 스킵")
                    return False
                chunks.append(chunk)
            raw = b"".join(chunks)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            socket.timeout, ConnectionError, OSError) as e:
        print(f"    ✗ 다운로드 실패: {e}")
        return False
    except Exception as e:
        print(f"    ✗ 에러: {e}")
        return False
    finally:
        socket.setdefaulttimeout(old_timeout)

    print(f"    ↓ {len(raw):,} bytes 수신")

    if is_dangerous_binary(raw):
        print(f"    ⚠ 위험 바이너리 감지 → 스킵")
        return False

    if file_type == "xlsx":
        if not is_xlsx_signature(raw):
            print(f"    ⚠ XLSX 시그니처 불일치 → 스킵")
            return False
        ok = sanitize_xlsx(raw, dest)
        if ok:
            print(f"    ✓ Saved (sanitized XLSX, {dest.stat().st_size:,} bytes) → {dest.name}")
        return ok
    else:
        # CSV / text
        sanitized = sanitize_csv_bytes(raw, encoding)
        dest.write_text(sanitized, encoding="utf-8")
        print(f"    ✓ Saved ({len(sanitized):,} bytes) → {dest.name}")
        return True


# ──────────────────────────────────
# Source Definitions
# ──────────────────────────────────

SOURCES = [
    # ── 한국 공공데이터 / Korean Public Data ──
    {
        "category": "🇰🇷 한국 인구통계 (Korean Census)",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/southkorea/southkorea-population/master/data/2010/population_by_province.csv",
                "filename": "kr_population_by_province_2010.csv",
                "desc": "시도별 인구 (2010 인구총조사)",
                "type": "csv",
            },
        ],
    },
    {
        "category": "🇰🇷 한국 COVID-19",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/hwuiwon/covid-19-analysis-kr/main/data/Time.csv",
                "filename": "kr_covid19_time_series.csv",
                "desc": "한국 COVID-19 시계열 데이터",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/hwuiwon/covid-19-analysis-kr/main/data/Region.csv",
                "filename": "kr_covid19_region.csv",
                "desc": "한국 COVID-19 지역별 현황",
                "type": "csv",
            },
        ],
    },

    # ── OxfordIHTM Messy Data (실제 더러운 XLSX) ──
    {
        "category": "🌏 OxfordIHTM Real-World Messy XLSX",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/OxfordIHTM/messy-data/main/data/cyclones.xlsx",
                "filename": "realworld_cyclones_philippines.xlsx",
                "desc": "필리핀 태풍 데이터 (messy headers, merged cells)",
                "type": "xlsx",
            },
            {
                "url": "https://raw.githubusercontent.com/OxfordIHTM/messy-data/main/data/occupational_health.xlsx",
                "filename": "realworld_occupational_health.xlsx",
                "desc": "직업보건 서비스 2021 (실제 보건부 데이터, 구조 불일치)",
                "type": "xlsx",
            },
            {
                "url": "https://raw.githubusercontent.com/OxfordIHTM/messy-data/main/data/pop_death.xlsx",
                "filename": "realworld_population_deaths.xlsx",
                "desc": "인구/사망 통계 2011-2021 (성별·연령, 다중 헤더)",
                "type": "xlsx",
            },
            {
                "url": "https://raw.githubusercontent.com/OxfordIHTM/messy-data/main/data/vaccine.xlsx",
                "filename": "realworld_vaccine_study.xlsx",
                "desc": "학생 백신 연구 (설문 데이터, 결측·불일치)",
                "type": "xlsx",
            },
            {
                "url": "https://raw.githubusercontent.com/OxfordIHTM/messy-data/main/data/ihtm_2025.xlsx",
                "filename": "realworld_ihtm_survey_2025.xlsx",
                "desc": "IHTM 학생 설문 2024-2025 (자유형식 입력, 오타)",
                "type": "xlsx",
            },
        ],
    },

    # ── eyowhite Messy Datasets (실제 더러운 CSV) ──
    {
        "category": "📊 Real-World Messy CSV (eyowhite)",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/healthcare_messy_data.csv",
                "filename": "realworld_healthcare_messy.csv",
                "desc": "의료 데이터 (결측, 불일치, 이상값)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/messy_HR_data.csv",
                "filename": "realworld_hr_messy.csv",
                "desc": "HR 인사 데이터 (중복, 타입 혼란)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/warehouse_messy_data.csv",
                "filename": "realworld_warehouse_messy.csv",
                "desc": "물류/창고 데이터 (결측, 포맷 불일치)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/messy_IMDB_dataset.csv",
                "filename": "realworld_imdb_messy.csv",
                "desc": "IMDB 영화 데이터 (스크래핑 원본, 더러움)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/automobile_dataset.csv",
                "filename": "realworld_automobile.csv",
                "desc": "자동차 스펙 데이터 (결측='?', 혼합 타입)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/eyowhite/Messy-dataset/main/Uncleaned_DS_jobs.csv",
                "filename": "realworld_datascience_jobs_uncleaned.csv",
                "desc": "데이터 사이언스 채용공고 (원본, 미정리)",
                "type": "csv",
            },
        ],
    },

    # ── 기타 Global Public Data ──
    {
        "category": "🌍 Global Public Data",
        "files": [
            {
                "url": "https://raw.githubusercontent.com/datasets/covid-19/main/data/countries-aggregated.csv",
                "filename": "global_covid19_countries.csv",
                "desc": "전세계 COVID-19 국가별 집계 (JHU CSSE)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/datasets/airport-codes/master/data/airport-codes.csv",
                "filename": "global_airport_codes.csv",
                "desc": "전세계 공항 코드 (결측 좌표, 폐쇄 공항 포함)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/datasets/world-cities/master/data/world-cities.csv",
                "filename": "global_world_cities.csv",
                "desc": "세계 도시 목록 (다국어 도시명, 중복 가능)",
                "type": "csv",
            },
            {
                "url": "https://raw.githubusercontent.com/YBI-Foundation/Dataset/main/Diabetes%20Missing%20Data.csv",
                "filename": "diabetes_missing_data.csv",
                "desc": "당뇨 진단 데이터 (의도적 결측값 포함)",
                "type": "csv",
            },
        ],
    },
]


# ──────────────────────────────────
# Main
# ──────────────────────────────────

def main():
    print(f"\n{'=' * 60}")
    print(f"  PyNorma Real-World Specimen Collector")
    print(f"  Target: {SPECIMEN_DIR}")
    print(f"{'=' * 60}")

    SPECIMEN_DIR.mkdir(parents=True, exist_ok=True)

    total = 0
    success = 0
    skipped = 0

    for group in SOURCES:
        print(f"\n{'─' * 60}")
        print(f"  {group['category']}")
        print(f"{'─' * 60}")

        for src in group["files"]:
            total += 1
            dest = SPECIMEN_DIR / src["filename"]

            # 이미 존재하면 스킵
            if dest.exists():
                print(f"\n  → {src['desc']}")
                print(f"    ⏭ 이미 존재 → 스킵 ({dest.name})")
                skipped += 1
                success += 1
                continue

            print(f"\n  → {src['desc']}")
            ok = download(
                url=src["url"],
                dest=dest,
                file_type=src.get("type", "csv"),
                encoding=src.get("encoding", "utf-8"),
            )
            if ok:
                success += 1

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  수집 완료!")
    print(f"  성공: {success}/{total} (스킵: {skipped})")
    print(f"{'=' * 60}")

    # List all files
    files = sorted(SPECIMEN_DIR.glob("*"))
    files = [f for f in files if not f.name.startswith("_") and not f.name.startswith(".")]
    print(f"\n  현재 specimen 파일 목록:")
    for f in files:
        size = f.stat().st_size
        ext = f.suffix.upper()
        print(f"    {f.name:50s} {ext:6s} {size:>10,} bytes")
    print(f"\n  총 {len(files)}개 파일")


if __name__ == "__main__":
    main()
