"""
benchmark_runner.py — Benchmark all strategies using TableRegion formulation.

Usage:
    python specimen/benchmark/benchmark_runner.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark.core import (
    TableRegion, Scores, compute_scores, quality_score,
    read_specimen, is_empty, is_numeric, row_fill_rate,
    grid_cols, has_summary_keyword,
)
from benchmark.strategies.strategy_a_rules import StrategyA
from benchmark.strategies.strategy_b_entropy import StrategyB
from benchmark.strategies.strategy_c_gradient import StrategyC
from benchmark.strategies.strategy_d_pattern import StrategyD
from benchmark.strategies.strategy_e_window import StrategyE
from benchmark.strategies.strategy_f_voting import StrategyF

SPECIMEN_DIR = Path(__file__).resolve().parent.parent
RESULT_DIR = SPECIMEN_DIR / "benchmark" / "results"

ALL_STRATEGIES = [StrategyA(), StrategyB(), StrategyC(),
                  StrategyD(), StrategyE(), StrategyF()]


# ──────────────────────────────────────────
# Ground Truth Generator
# ──────────────────────────────────────────

def generate_ground_truth(grid: list[list[str]]) -> list[TableRegion]:
    """Auto-generate ground truth as list[TableRegion]."""
    if not grid:
        return []

    n = len(grid)
    ncols = grid_cols(grid)

    # Header: first text-dominant row with fill > 0.5
    header = 0
    for i in range(min(n, 30)):
        non_empty = [c for c in grid[i] if not is_empty(c)]
        if len(non_empty) < 2:
            continue
        text_ratio = sum(1 for c in non_empty if not is_numeric(c)) / len(non_empty)
        if text_ratio > 0.5:
            header = i
            break

    top = header + 1

    # Bottom: last row with fill >= 0.3 and 2+ non-empty cells
    bottom = n - 1
    for i in range(n - 1, top - 1, -1):
        non_empty = [c for c in grid[i] if not is_empty(c)]
        if len(non_empty) >= 2 and row_fill_rate(grid[i]) >= 0.3:
            bottom = i
            break

    # Column boundaries: 10%+ fill in data rows
    data_idxs = [i for i in range(top, bottom + 1)
                 if row_fill_rate(grid[i]) > 0 and not has_summary_keyword(grid[i])]
    left, right = 0, ncols
    if data_idxs:
        for c in range(ncols):
            filled = sum(1 for i in data_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
            if filled / len(data_idxs) >= 0.1:
                left = c
                break
        for c in range(ncols - 1, left - 1, -1):
            filled = sum(1 for i in data_idxs if c < len(grid[i]) and not is_empty(grid[i][c]))
            if filled / len(data_idxs) >= 0.1:
                right = c + 1
                break

    return [TableRegion(header=header, top=top, left=left, bottom=bottom, right=right)]


# ──────────────────────────────────────────
# Benchmark
# ──────────────────────────────────────────

def run_benchmark():
    RESULT_DIR.mkdir(parents=True, exist_ok=True)

    files = sorted(SPECIMEN_DIR.glob("*"))
    files = [f for f in files if f.is_file()
             and not f.name.startswith("_")
             and not f.name.startswith(".")
             and f.suffix.lower() in (".csv", ".xlsx")]

    print(f"\n{'═' * 80}")
    print(f"  PyNorma Ensemble Benchmark v2 (TableRegion)")
    print(f"  {datetime.now().isoformat()}")
    print(f"  Strategies: {len(ALL_STRATEGIES)} | Files: {len(files)}")
    print(f"{'═' * 80}\n")

    results: dict[str, dict[str, Scores]] = defaultdict(dict)
    timings: dict[str, dict[str, float]] = defaultdict(dict)
    qscores: dict[str, dict[str, float]] = defaultdict(dict)

    for fpath in files:
        print(f"{'─' * 80}")
        print(f"  📄 {fpath.name}")

        try:
            grid, meta = read_specimen(fpath)
        except Exception as e:
            print(f"    ✗ Read failed: {e}")
            continue
        if not grid:
            print(f"    ⏭ Empty")
            continue

        gt = generate_ground_truth(grid)
        gt0 = gt[0] if gt else TableRegion(0, 1, 0, len(grid) - 1, grid_cols(grid))
        print(f"    GT: header={gt0.header} data=[{gt0.top}..{gt0.bottom}] "
              f"cols=[{gt0.left}..{gt0.right}) ({gt0.right - gt0.left} cols)")

        for strategy in ALL_STRATEGIES:
            t0 = time.perf_counter()
            try:
                regions = strategy.detect(grid)
                elapsed = time.perf_counter() - t0
                scores = compute_scores(regions, gt, grid)
                qs = quality_score(grid, regions[0]) if regions else 0.0

                results[strategy.name][fpath.name] = scores
                timings[strategy.name][fpath.name] = elapsed
                qscores[strategy.name][fpath.name] = qs

                r0 = regions[0] if regions else TableRegion(-1, 0, 0, 0, 0)
                print(f"    [{strategy.name:10s}] "
                      f"({r0.header},{r0.top},{r0.left},{r0.bottom},{r0.right}) "
                      f"hdr={scores.header_accuracy:.2f} iou={scores.boundary_iou:.2f} "
                      f"nrm={scores.noise_removal:.2f} prv={scores.data_preservation:.2f} "
                      f"cln={scores.cleaning_quality:.2f} → avg={scores.avg:.3f} "
                      f"qs={qs:.3f} ({elapsed*1000:.0f}ms)")
            except Exception as e:
                print(f"    [{strategy.name:10s}] ✗ {e}")
                results[strategy.name][fpath.name] = Scores()
                timings[strategy.name][fpath.name] = 0
                qscores[strategy.name][fpath.name] = 0

    # Auto-select simulation
    print(f"\n{'═' * 80}")
    print(f"  AUTO-SELECT SIMULATION (quality_score picks best)")
    print(f"{'═' * 80}")

    auto_scores = []
    oracle_scores = []
    for fpath in files:
        fname = fpath.name
        # Auto: pick strategy with highest quality_score
        best_qs_name = max(
            (s.name for s in ALL_STRATEGIES if fname in qscores[s.name]),
            key=lambda name: qscores[name].get(fname, 0),
            default=None)
        # Oracle: pick strategy with highest benchmark score
        best_bm_name = max(
            (s.name for s in ALL_STRATEGIES if fname in results[s.name]),
            key=lambda name: results[name].get(fname, Scores()).avg,
            default=None)

        if best_qs_name and fname in results[best_qs_name]:
            auto_s = results[best_qs_name][fname].avg
            auto_scores.append(auto_s)
            oracle_s = results[best_bm_name][fname].avg if best_bm_name else 0
            oracle_scores.append(oracle_s)
            match = "✓" if best_qs_name == best_bm_name else "✗"
            print(f"  {match} {fname:45s} auto={best_qs_name} ({auto_s:.3f})  "
                  f"oracle={best_bm_name} ({oracle_s:.3f})")

    if auto_scores:
        print(f"\n  Auto-select avg:  {sum(auto_scores)/len(auto_scores):.3f}")
        print(f"  Oracle avg:       {sum(oracle_scores)/len(oracle_scores):.3f}")

    generate_report(files, ALL_STRATEGIES, results, timings, qscores)
    generate_json(files, ALL_STRATEGIES, results, timings, qscores)


# ──────────────────────────────────────────
# Report
# ──────────────────────────────────────────

def generate_report(files, strategies, results, timings, qscores):
    report_path = RESULT_DIR / "benchmark_results.md"
    L = []
    L.append("# Ensemble Preprocessor Benchmark v2 (TableRegion)")
    L.append(f"\nGenerated: {datetime.now().isoformat()}")
    L.append(f"\n**{len(strategies)} strategies × {len(files)} files = "
             f"{len(strategies)*len(files)} experiments**\n")
    L.append("## Problem Formulation\n")
    L.append("```")
    L.append("Input:  raw 2D grid (r × c)")
    L.append("Output: N tables × (header, top, left, bottom, right)")
    L.append("```\n")

    # Leaderboard
    L.append("## Leaderboard\n")
    L.append("| Rank | Strategy | Header | IoU | Noise | Preserve | Clean | **AVG** | Avg Time |")
    L.append("|------|----------|--------|-----|-------|----------|-------|---------|----------|")

    board = []
    for s in strategies:
        sc = list(results[s.name].values())
        if not sc:
            continue
        n_ = len(sc)
        h = sum(x.header_accuracy for x in sc) / n_
        i_ = sum(x.boundary_iou for x in sc) / n_
        nr = sum(x.noise_removal for x in sc) / n_
        p = sum(x.data_preservation for x in sc) / n_
        c = sum(x.cleaning_quality for x in sc) / n_
        avg = (h + i_ + nr + p + c) / 5
        t = sum(timings[s.name].values()) / n_ * 1000
        board.append((avg, s.name, h, i_, nr, p, c, t))

    board.sort(reverse=True)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for rank, (avg, name, h, i_, n_, p, c, t) in enumerate(board, 1):
        m = medals.get(rank, f" {rank}")
        L.append(f"| {m} | **{name}** | {h:.3f} | {i_:.3f} | {n_:.3f} | "
                 f"{p:.3f} | {c:.3f} | **{avg:.3f}** | {t:.0f}ms |")

    # Auto-select accuracy
    L.append("\n## Auto-Select (quality_score)\n")
    auto_match, auto_total = 0, 0
    auto_avg, oracle_avg = [], []
    for fpath in files:
        fname = fpath.name
        best_qs = max((s.name for s in strategies if fname in qscores[s.name]),
                      key=lambda n: qscores[n].get(fname, 0), default=None)
        best_bm = max((s.name for s in strategies if fname in results[s.name]),
                      key=lambda n: results[n].get(fname, Scores()).avg, default=None)
        if best_qs and best_bm:
            auto_total += 1
            if best_qs == best_bm:
                auto_match += 1
            auto_avg.append(results[best_qs][fname].avg)
            oracle_avg.append(results[best_bm][fname].avg)

    if auto_total:
        L.append(f"- Strategy selection accuracy: **{auto_match}/{auto_total}** "
                 f"({100*auto_match/auto_total:.0f}%)")
        L.append(f"- Auto-select avg score: **{sum(auto_avg)/len(auto_avg):.3f}**")
        L.append(f"- Oracle (perfect select) avg: **{sum(oracle_avg)/len(oracle_avg):.3f}**")
        gap = sum(oracle_avg)/len(oracle_avg) - sum(auto_avg)/len(auto_avg)
        L.append(f"- Quality score gap vs oracle: **{gap:.3f}**")

    # Per-file detail
    L.append("\n## Per-File Detail\n")
    L.append("| File | GT Region | Best Strategy | Score | Auto Pick | Auto Score |")
    L.append("|------|-----------|---------------|-------|-----------|------------|")
    for fpath in files:
        fname = fpath.name
        file_scores = [(s.name, results[s.name].get(fname, Scores())) for s in strategies]
        file_scores.sort(key=lambda x: x[1].avg, reverse=True)
        best_name, best_sc = file_scores[0] if file_scores else ("", Scores())
        best_qs = max((s.name for s in strategies if fname in qscores[s.name]),
                      key=lambda n: qscores[n].get(fname, 0), default="")
        auto_sc = results.get(best_qs, {}).get(fname, Scores())
        short = fname[:35] + "…" if len(fname) > 35 else fname
        L.append(f"| `{short}` | - | {best_name} | {best_sc.avg:.3f} | "
                 f"{best_qs} | {auto_sc.avg:.3f} |")

    report_path.write_text("\n".join(L), encoding="utf-8")
    print(f"\n📊 Report: {report_path}")


def generate_json(files, strategies, results, timings, qscores):
    json_path = RESULT_DIR / "benchmark_raw.json"
    data = {}
    for s in strategies:
        data[s.name] = {}
        for fpath in files:
            fname = fpath.name
            sc = results[s.name].get(fname, Scores())
            data[s.name][fname] = {
                "header_accuracy": round(sc.header_accuracy, 4),
                "boundary_iou": round(sc.boundary_iou, 4),
                "noise_removal": round(sc.noise_removal, 4),
                "data_preservation": round(sc.data_preservation, 4),
                "cleaning_quality": round(sc.cleaning_quality, 4),
                "avg": round(sc.avg, 4),
                "quality_score": round(qscores[s.name].get(fname, 0), 4),
                "time_ms": round(timings[s.name].get(fname, 0) * 1000, 1),
            }
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📊 JSON: {json_path}")


if __name__ == "__main__":
    run_benchmark()
