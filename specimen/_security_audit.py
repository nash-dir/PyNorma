"""
specimen Security Audit Script
================================
specimen 폴더 내 모든 파일에 대해 잠재적 위험요소를 검사.

검사 항목:
1. 바이너리 시그니처 (PE exe, ELF, OLE macro xls, PDF)
2. CSV Injection (=, +, -, @, TAB, CR, LF 로 시작하는 셀)
3. XLSX 매크로/VBA (vbaProject.bin 포함 여부)
4. Null byte / 제어문자
5. 의심스러운 패턴 (script 태그, powershell, cmd, 등)
6. 파일 확장자 vs 실제 내용 불일치
"""

from __future__ import annotations

import csv
import io
import os
import re
import zipfile
from pathlib import Path
from collections import defaultdict

SPECIMEN_DIR = Path(__file__).resolve().parent

# ─── Colors for terminal ───
class C:
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def check_binary_signatures(raw: bytes) -> list[str]:
    """위험 바이너리 시그니처 검사."""
    findings = []
    sigs = {
        b"\x4d\x5a": "PE Executable (Windows EXE/DLL)",
        b"\x7fELF": "ELF Executable (Linux)",
        b"\xd0\xcf\x11\xe0": "OLE2 (구형 xls/doc, 매크로 가능)",
        b"\x25\x50\x44\x46": "PDF",
        b"\xca\xfe\xba\xbe": "Java Class / Mach-O Fat Binary",
        b"MZ": "PE Executable (alt)",
    }
    for sig, desc in sigs.items():
        if raw[:len(sig)] == sig:
            findings.append(f"🔴 바이너리 시그니처 감지: {desc}")
    return findings


def check_null_bytes(raw: bytes) -> list[str]:
    """Null byte 검사."""
    findings = []
    count = raw.count(b"\x00")
    if count > 0:
        findings.append(f"⚠️ Null byte {count}개 발견")
    return findings


def check_csv_injection(text: str, filename: str) -> list[str]:
    """CSV Injection 패턴 검사."""
    findings = []
    dangerous_prefixes = ("=", "+", "-", "@", "\t", "\r", "\n")
    injection_count = 0
    injection_examples = []

    try:
        reader = csv.reader(io.StringIO(text))
        for row_num, row in enumerate(reader, 1):
            for col_num, cell in enumerate(row):
                cell_stripped = cell.strip()
                if cell_stripped and cell_stripped[0] in dangerous_prefixes:
                    # '-' 다음에 숫자가 오면 음수이므로 무시
                    if cell_stripped[0] == "-" and len(cell_stripped) > 1:
                        rest = cell_stripped[1:]
                        try:
                            float(rest.replace(",", ""))
                            continue  # 음수
                        except ValueError:
                            pass
                    # '+' 다음에 숫자가 오면 양수이므로 무시
                    if cell_stripped[0] == "+" and len(cell_stripped) > 1:
                        rest = cell_stripped[1:]
                        try:
                            float(rest.replace(",", ""))
                            continue
                        except ValueError:
                            pass

                    injection_count += 1
                    if len(injection_examples) < 5:
                        preview = cell_stripped[:60]
                        injection_examples.append(
                            f"  Row {row_num}, Col {col_num + 1}: {preview!r}"
                        )
    except csv.Error:
        findings.append("⚠️ CSV 파싱 에러 (비정상 구조)")

    if injection_count > 0:
        findings.append(f"⚠️ CSV Injection 위험 셀 {injection_count}개 (=,+,-,@ 등으로 시작)")
        findings.extend(injection_examples)
        if injection_count > 5:
            findings.append(f"  ... 외 {injection_count - 5}개 더")

    return findings


def check_suspicious_patterns(text: str) -> list[str]:
    """의심스러운 스크립트 패턴 검사."""
    findings = []
    patterns = {
        r"<script[\s>]": "HTML <script> 태그",
        r"javascript:": "JavaScript URI",
        r"vbscript:": "VBScript URI",
        r"on(click|load|error|mouseover)\s*=": "HTML 이벤트 핸들러",
        r"cmd\.exe|powershell|/bin/(ba)?sh": "쉘 실행 명령",
        r"WScript\.Shell|Shell\.Application": "Windows Script Host",
        r"CreateObject\s*\(": "VBA CreateObject",
        r"IMPORTXML|IMPORTDATA|IMPORTRANGE": "Google Sheets 외부 데이터 함수",
        r"=CMD\(|=EXEC\(|=SYSTEM\(": "수식 기반 명령 실행",
        r"HYPERLINK\s*\(.*https?://": "수식 기반 하이퍼링크 (피싱 가능)",
    }
    for pattern, desc in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            findings.append(f"⚠️ 의심 패턴 발견: {desc} ({len(matches)}건)")

    return findings


def check_xlsx_macros(filepath: Path) -> list[str]:
    """XLSX 내부에 VBA 매크로, 외부 링크 등 검사."""
    findings = []
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            names = zf.namelist()

            # VBA 매크로 검사
            vba_files = [n for n in names if "vbaProject" in n.lower() or n.endswith(".bin")]
            if vba_files:
                findings.append(f"🔴 VBA 매크로 파일 발견: {vba_files}")

            # 외부 연결 검사
            ext_links = [n for n in names if "externalLink" in n.lower()]
            if ext_links:
                findings.append(f"⚠️ 외부 링크 참조 발견: {len(ext_links)}개")

            # ActiveX 검사
            activex = [n for n in names if "activeX" in n.lower()]
            if activex:
                findings.append(f"🔴 ActiveX 컨트롤 발견: {len(activex)}개")

            # Printer settings (가끔 exploit 벡터)
            printers = [n for n in names if "printerSettings" in n.lower()]
            if printers:
                findings.append(f"⚠️ 프린터 설정 포함: {len(printers)}개 (잠재적 exploit 벡터)")

            # 파일 내 의심스러운 문자열 검사 (XML 내용)
            for name in names:
                if name.endswith((".xml", ".rels")):
                    try:
                        content = zf.read(name).decode("utf-8", errors="replace")
                        if "cmd.exe" in content.lower() or "powershell" in content.lower():
                            findings.append(f"🔴 XLSX XML에 쉘 명령 발견: {name}")
                        if "DDE" in content or "ddeLink" in content.lower():
                            findings.append(f"🔴 DDE 공격 패턴 발견: {name}")
                    except Exception:
                        pass

    except zipfile.BadZipFile:
        findings.append("🔴 손상된 ZIP/XLSX 파일")
    except Exception as e:
        findings.append(f"⚠️ XLSX 검사 에러: {e}")

    return findings


def check_extension_mismatch(filepath: Path, raw: bytes) -> list[str]:
    """확장자와 실제 내용 불일치 검사."""
    findings = []
    ext = filepath.suffix.lower()

    if ext == ".csv":
        # CSV인데 실제로는 ZIP/XLSX인 경우
        if raw[:4] == b"\x50\x4b\x03\x04":
            findings.append("🔴 확장자 .csv이지만 실제 내용은 ZIP/XLSX")
        elif raw[:4] == b"\xd0\xcf\x11\xe0":
            findings.append("🔴 확장자 .csv이지만 실제 내용은 OLE2 (구형 Excel)")
    elif ext == ".xlsx":
        if raw[:4] != b"\x50\x4b\x03\x04":
            findings.append("🔴 확장자 .xlsx이지만 ZIP 시그니처 없음")

    return findings


# ─── Main Audit ───

def audit_file(filepath: Path) -> dict:
    """단일 파일 보안 감사."""
    result = {
        "file": filepath.name,
        "size": filepath.stat().st_size,
        "findings": [],
        "severity": "CLEAN",  # CLEAN, WARNING, DANGER
    }

    raw = filepath.read_bytes()

    # 1. 바이너리 시그니처
    result["findings"].extend(check_binary_signatures(raw))

    # 2. 확장자 불일치
    result["findings"].extend(check_extension_mismatch(filepath, raw))

    # 3. Null bytes (CSV만)
    if filepath.suffix.lower() == ".csv":
        result["findings"].extend(check_null_bytes(raw))

    # 4. CSV 내용 검사
    if filepath.suffix.lower() == ".csv":
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = raw.decode("latin-1", errors="replace")

        result["findings"].extend(check_csv_injection(text, filepath.name))
        result["findings"].extend(check_suspicious_patterns(text))

    # 5. XLSX 매크로/VBA 검사
    if filepath.suffix.lower() == ".xlsx":
        result["findings"].extend(check_xlsx_macros(filepath))

    # Severity 결정
    for f in result["findings"]:
        if "🔴" in f:
            result["severity"] = "DANGER"
            break
        elif "⚠️" in f:
            result["severity"] = "WARNING"

    return result


def main():
    print(f"\n{'═' * 70}")
    print(f"  {C.BOLD}PyNorma Specimen Security Audit{C.RESET}")
    print(f"  Target: {SPECIMEN_DIR}")
    print(f"{'═' * 70}")

    files = sorted(SPECIMEN_DIR.glob("*"))
    files = [f for f in files if f.is_file() and not f.name.startswith("_") and not f.name.startswith(".")]

    stats = defaultdict(int)
    all_results = []

    for filepath in files:
        result = audit_file(filepath)
        all_results.append(result)
        stats[result["severity"]] += 1

        severity_color = {
            "CLEAN": C.GREEN,
            "WARNING": C.YELLOW,
            "DANGER": C.RED,
        }
        color = severity_color.get(result["severity"], C.RESET)

        print(f"\n{'─' * 70}")
        print(f"  {C.CYAN}{result['file']}{C.RESET} ({result['size']:,} bytes)")
        print(f"  Status: {color}{C.BOLD}{result['severity']}{C.RESET}")

        if result["findings"]:
            for finding in result["findings"]:
                print(f"    {finding}")
        else:
            print(f"    {C.GREEN}✓ 위험요소 없음{C.RESET}")

    # Summary
    print(f"\n{'═' * 70}")
    print(f"  {C.BOLD}감사 결과 요약{C.RESET}")
    print(f"{'═' * 70}")
    print(f"  검사 파일: {len(files)}개")
    print(f"  {C.GREEN}✓ CLEAN:   {stats['CLEAN']}개{C.RESET}")
    print(f"  {C.YELLOW}⚠ WARNING: {stats['WARNING']}개{C.RESET}")
    print(f"  {C.RED}✗ DANGER:  {stats['DANGER']}개{C.RESET}")

    if stats["DANGER"] > 0:
        print(f"\n  {C.RED}{C.BOLD}⚠ 위험 파일이 발견되었습니다! 즉시 확인 필요.{C.RESET}")
    elif stats["WARNING"] > 0:
        print(f"\n  {C.YELLOW}⚠ 경고 항목이 있으나 대부분 의도된 '더러운 데이터' 특성입니다.{C.RESET}")
        print(f"  {C.YELLOW}  CSV Injection 접두어는 전처리 실험 대상이므로 정상입니다.{C.RESET}")
    else:
        print(f"\n  {C.GREEN}{C.BOLD}✓ 모든 파일이 안전합니다.{C.RESET}")

    print(f"\n{'═' * 70}\n")

    return stats["DANGER"]


if __name__ == "__main__":
    exit(main())
