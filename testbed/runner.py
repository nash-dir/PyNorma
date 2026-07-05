"""
testbed/runner.py — Evaluate the shipping pynorma.Pipeline against ground-truth labels.

Unlike specimen/benchmark/benchmark_runner.py (which scores 6 internal strategies
against *auto-generated* ground truth), this runner:

  * exercises the REAL public API — ``pynorma.Pipeline(path).detect().clean()`` —
  * compares its output to HUMAN-VERIFIED ground truth in ``manifest.json``, and
  * emits a scorecard (region IoU, header accuracy, table-count, cleaned shape,
    and 1NF/multi-valued-column recall).

Ground-truth region convention (0-indexed, see manifest.json → labeling_spec):
    header : row index of the column-name row (-1 if the table has no header)
    top    : first DATA row (inclusive)
    left   : first DATA column (inclusive)
    bottom : last  DATA row (inclusive)
    right  : last  DATA column (EXCLUSIVE)

Usage:
    python testbed/runner.py                 # evaluate auto-select Pipeline
    python testbed/runner.py --strategy D    # force one strategy
    python testbed/runner.py --all-strategies  # add a per-strategy comparison table
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

TESTBED_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTBED_DIR.parent
DATA_DIR = TESTBED_DIR / "data"
MANIFEST = TESTBED_DIR / "manifest.json"
RESULTS_DIR = TESTBED_DIR / "results"

# Make the pynorma package importable when run from anywhere.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

IOU_PASS = 0.60          # region IoU threshold for a "pass"
ROW_TOL = 0.15           # cleaned-row-count tolerance (fraction) for the informational check


# ──────────────────────────────────────────────────────────────
# Geometry helpers (standalone — no dependency on the GT generator)
# ──────────────────────────────────────────────────────────────

def _region_cells(reg: dict) -> set:
    """Cell coordinates (data area only) of a region dict."""
    top, left, bottom, right = reg["top"], reg["left"], reg["bottom"], reg["right"]
    return {(r, c) for r in range(top, bottom + 1) for c in range(left, right)}


def _iou(a: dict, b: dict) -> float:
    ca, cb = _region_cells(a), _region_cells(b)
    if not ca and not cb:
        return 1.0
    inter = len(ca & cb)
    union = len(ca | cb)
    return inter / union if union else 0.0


def _match_regions(pred: list[dict], gt: list[dict]) -> tuple[float, float]:
    """Greedy best-match IoU + header accuracy over matched (pred, gt) pairs.

    Returns (mean_iou, mean_header_acc). Unmatched GT tables score 0 IoU.
    """
    if not gt:
        return (1.0 if not pred else 0.0), (1.0 if not pred else 0.0)
    if not pred:
        return 0.0, 0.0

    used = set()
    ious, headers = [], []
    for g in gt:
        best_iou, best_j = 0.0, -1
        for j, p in enumerate(pred):
            if j in used:
                continue
            v = _iou(p, g)
            if v > best_iou:
                best_iou, best_j = v, j
        if best_j >= 0:
            used.add(best_j)
            ious.append(best_iou)
            headers.append(1.0 / (1.0 + abs(pred[best_j]["header"] - g["header"])))
        else:
            ious.append(0.0)
            headers.append(0.0)
    return sum(ious) / len(ious), sum(headers) / len(headers)


def _region_from_tablergion(tr) -> dict:
    """Convert a benchmark TableRegion namedtuple to a plain dict."""
    return {"header": tr.header, "top": tr.top, "left": tr.left,
            "bottom": tr.bottom, "right": tr.right}


# ──────────────────────────────────────────────────────────────
# Evaluation of one file
# ──────────────────────────────────────────────────────────────

def evaluate_file(entry: dict, *, strategy: str | None) -> dict:
    from pynorma import Pipeline, detect_multivalue_columns

    fpath = DATA_DIR / entry["file"]
    gt = entry["ground_truth"]
    gt_regions = gt["regions"]

    res: dict = {
        "name": entry["name"],
        "file": entry["file"],
        "difficulty": entry.get("difficulty"),
        "tags": entry.get("messiness_tags", []),
        "gt_n_tables": gt.get("n_tables", len(gt_regions)),
    }

    if not fpath.exists():
        res["status"] = "missing"
        res["note"] = "data file not present — run: python testbed/fetch.py"
        return res

    t0 = time.perf_counter()
    try:
        p = Pipeline(str(fpath), strategy=strategy)
        p.detect().clean()
        pred_regions = [_region_from_tablergion(r) for r in getattr(p, "_regions", [])]
        pred_tables = p.all_tables()
    except Exception as e:  # noqa: BLE001 — the whole point is to catch library failures
        res["status"] = "error"
        res["error"] = f"{type(e).__name__}: {e}"
        res["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return res
    res["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)

    iou, hdr = _match_regions(pred_regions, gt_regions)
    count_match = len(pred_tables) == res["gt_n_tables"]

    res["status"] = "ok"
    res["pred_n_tables"] = len(pred_tables)
    res["count_match"] = count_match
    res["region_iou"] = round(iou, 3)
    res["header_acc"] = round(hdr, 3)

    # Cleaned-shape check on the primary table.
    prim = gt.get("primary", {})
    if pred_tables:
        pr, pc = pred_tables[0].shape
        res["pred_shape"] = [pr, pc]
        exp_cols = prim.get("clean_cols")
        res["cols_match"] = (exp_cols is None) or (pc == exp_cols)
        exp_rows = prim.get("clean_rows")
        if exp_rows:
            lo, hi = exp_rows * (1 - ROW_TOL), exp_rows * (1 + ROW_TOL)
            res["rows_ok"] = lo <= pr <= hi
    else:
        res["pred_shape"] = None
        res["cols_match"] = False

    # 1NF / multi-valued-column recall (only where GT declares expectations).
    mv_expected = gt.get("multivalue_columns")
    if mv_expected is not None and pred_tables:
        try:
            found = {name for name, *_ in detect_multivalue_columns(pred_tables[0])}
        except Exception as e:  # noqa: BLE001
            found = set()
            res["mv_error"] = f"{type(e).__name__}: {e}"
        hit = sorted(set(mv_expected) & found)
        res["mv_expected"] = mv_expected
        res["mv_found"] = sorted(found)
        res["mv_recall"] = round(len(hit) / len(mv_expected), 3) if mv_expected else 1.0

    res["pass"] = bool(count_match and iou >= IOU_PASS and res.get("cols_match", False))
    return res


# ──────────────────────────────────────────────────────────────
# Reporting
# ──────────────────────────────────────────────────────────────

def _agg(rows: list[dict], key: str, pred=lambda r: r.get("pass")):
    """Group pass-rate by an entry attribute."""
    buckets: dict = {}
    for r in rows:
        if r.get("status") != "ok":
            continue
        k = r.get(key)
        for kk in (k if isinstance(k, list) else [k]):
            b = buckets.setdefault(kk, [0, 0])
            b[1] += 1
            if pred(r):
                b[0] += 1
    return buckets


def write_report(rows: list[dict], meta: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    evaluated = [r for r in rows if r.get("status") == "ok"]
    missing = [r for r in rows if r.get("status") == "missing"]
    errors = [r for r in rows if r.get("status") == "error"]
    n = len(evaluated)
    passed = sum(1 for r in evaluated if r.get("pass"))
    mean_iou = sum(r["region_iou"] for r in evaluated) / n if n else 0.0
    mean_hdr = sum(r["header_acc"] for r in evaluated) / n if n else 0.0
    count_ok = sum(1 for r in evaluated if r.get("count_match"))

    # Raw JSON (gitignored).
    raw = {"meta": meta, "results": rows}
    (RESULTS_DIR / "scorecard.raw.json").write_text(
        json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")

    L = []
    L.append("# PyNorma Testbed — Scorecard")
    L.append(f"\nGenerated: {meta['generated']}  |  strategy: `{meta['strategy']}`  |  "
             f"pynorma {meta.get('pynorma_version','?')}")
    L.append(f"\nEvaluates the shipping `pynorma.Pipeline` against **human-verified** "
             f"ground truth (`manifest.json`).\n")
    L.append("## Summary\n")
    L.append(f"- Files evaluated: **{n}**  (missing: {len(missing)}, errors: {len(errors)})")
    if n:
        L.append(f"- **Pass rate: {passed}/{n} ({100*passed/n:.0f}%)**  "
                 f"— pass = table-count match AND region IoU ≥ {IOU_PASS:.2f} AND column-count match")
        L.append(f"- Mean region IoU: **{mean_iou:.3f}**")
        L.append(f"- Mean header accuracy: **{mean_hdr:.3f}**")
        L.append(f"- Table-count match: **{count_ok}/{n}**")

    # Breakdown by difficulty.
    diff = _agg(evaluated, "difficulty")
    if diff:
        L.append("\n## Pass rate by difficulty\n")
        L.append("| Difficulty | Pass | Total | Rate |")
        L.append("|---|---|---|---|")
        order = {"easy": 0, "medium": 1, "hard": 2, "adversarial": 3}
        for k in sorted(diff, key=lambda x: order.get(x, 9)):
            p, t = diff[k]
            L.append(f"| {k} | {p} | {t} | {100*p/t:.0f}% |")

    # Per-file detail.
    L.append("\n## Per-file results\n")
    L.append("| File | Diff | GT×Pred tables | IoU | Hdr | Cols | Shape | 1NF | Pass | ms |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        name = r["name"]
        if r["status"] == "missing":
            L.append(f"| `{name}` | {r.get('difficulty','')} | — | — | — | — | — | — | ⏭ miss | — |")
            continue
        if r["status"] == "error":
            L.append(f"| `{name}` | {r.get('difficulty','')} | — | — | — | — | — | — | ✗ err | "
                     f"{r.get('elapsed_ms','')} |")
            continue
        cnt = f"{r['gt_n_tables']}×{r['pred_n_tables']}" + ("" if r["count_match"] else "⚠")
        cols = "✓" if r.get("cols_match") else "✗"
        shape = f"{r['pred_shape'][0]}×{r['pred_shape'][1]}" if r.get("pred_shape") else "—"
        mv = f"{r['mv_recall']:.2f}" if "mv_recall" in r else "—"
        pf = "✅" if r.get("pass") else "❌"
        L.append(f"| `{name}` | {r.get('difficulty','')} | {cnt} | {r['region_iou']:.2f} | "
                 f"{r['header_acc']:.2f} | {cols} | {shape} | {mv} | {pf} | {r['elapsed_ms']:.0f} |")

    if errors:
        L.append("\n## Errors\n")
        for r in errors:
            L.append(f"- `{r['name']}`: {r.get('error')}")

    out = RESULTS_DIR / "scorecard.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\n📊 Scorecard: {out}")
    print(f"📊 Raw JSON:  {RESULTS_DIR / 'scorecard.raw.json'} (gitignored)")
    if n:
        print(f"\n  Pass {passed}/{n} ({100*passed/n:.0f}%) | "
              f"IoU {mean_iou:.3f} | header {mean_hdr:.3f} | count {count_ok}/{n}")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main() -> int:
    global DATA_DIR
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strategy", default=None,
                    help="Detection strategy A–F, or omit for auto-select.")
    ap.add_argument("--manifest", default=str(MANIFEST))
    ap.add_argument("--data", default=str(DATA_DIR))
    ap.add_argument("--only", default=None,
                    help="Comma-separated list of names to evaluate (default: all).")
    args = ap.parse_args()

    DATA_DIR = Path(args.data)

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    entries = manifest["files"]
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        entries = [e for e in entries if e["name"] in wanted]

    try:
        import pynorma
        pyn_ver = getattr(pynorma, "__version__", "?")
    except Exception:
        pyn_ver = "?"

    print(f"\n{'═'*74}")
    print(f"  PyNorma Testbed Runner  |  {len(entries)} files  |  "
          f"strategy={args.strategy or 'auto'}")
    print(f"{'═'*74}")

    rows = []
    for e in entries:
        r = evaluate_file(e, strategy=args.strategy)
        rows.append(r)
        st = r["status"]
        if st == "ok":
            flag = "✅" if r.get("pass") else "❌"
            print(f"  {flag} {r['name']:44s} IoU={r['region_iou']:.2f} "
                  f"hdr={r['header_acc']:.2f} tbl={r['gt_n_tables']}×{r['pred_n_tables']} "
                  f"{r['elapsed_ms']:.0f}ms")
        elif st == "error":
            print(f"  ✗  {r['name']:44s} {r.get('error')}")
        else:
            print(f"  ⏭  {r['name']:44s} (missing — run fetch.py)")

    meta = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "strategy": args.strategy or "auto",
        "pynorma_version": pyn_ver,
        "iou_pass": IOU_PASS,
        "n_files": len(entries),
    }
    write_report(rows, meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
