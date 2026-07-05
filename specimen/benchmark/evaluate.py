"""
evaluate.py — Honest end-to-end evaluation against hand-labeled ground truth.

The only metric that matters for the project goal ("any tabular data → long
form") is: does the pipeline's final long-form output match the long-form
output derived from human-labeled structure?

For each specimen:
  1. GT  : hand-labeled TableModels (ground_truth.json) → to_long → row multiset
  2. Pred: detect() → build_table_model() → to_long → row multiset
  3. Score: cell-level precision / recall / F1 over long-row multisets.

Both sides run through the same to_long converter, so this isolates and
measures *structure detection* correctness (region + header block + stub),
not converter quirks.

Usage:
    python -m benchmark.evaluate            # from specimen/
    python specimen/benchmark/evaluate.py   # from repo root
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pynorma.detect.core import TableModel, read_specimen, build_table_model, to_long
from pynorma.detect.preprocess import detect

SPECIMEN_DIR = Path(__file__).resolve().parent.parent
GT_PATH = Path(__file__).resolve().parent / "ground_truth.json"
RESULTS_PATH = Path(__file__).resolve().parent / "eval_results.json"


def load_ground_truth() -> dict[str, list[TableModel]]:
    """Load hand-labeled models keyed by filename."""
    raw = json.loads(GT_PATH.read_text(encoding="utf-8"))
    gt = {}
    for fname, tables in raw["files"].items():
        models = []
        for t in tables:
            hr = t["header_rows"]
            models.append(TableModel(
                header_rows=tuple(hr) if hr is not None else None,
                stub_end=t["stub_end"],
                top=t["top"], left=t["left"],
                bottom=t["bottom"], right=t["right"],
            ))
        gt[fname] = models
    return gt


def long_rows(grid: list[list[str]], models: list[TableModel]) -> Counter:
    """Multiset of long-form rows produced by a set of table models."""
    bag: Counter = Counter()
    for m in models:
        try:
            _, rows = to_long(grid, m)
        except Exception:
            continue
        bag.update(tuple(r) for r in rows)
    return bag


def score_file(pred: Counter, gt: Counter) -> dict:
    """Cell-level precision/recall/F1 between predicted and GT long rows."""
    tp = sum((pred & gt).values())
    n_pred = sum(pred.values())
    n_gt = sum(gt.values())
    precision = tp / n_pred if n_pred else (1.0 if not n_gt else 0.0)
    recall = tp / n_gt if n_gt else 1.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) > 0 else 0.0)
    return {"tp": tp, "pred": n_pred, "gt": n_gt,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4)}


def evaluate(files: list[str] | None = None, *, verbose: bool = True) -> dict:
    """Run the full evaluation. Returns {file: scores, "_aggregate": {...}}."""
    gt_all = load_ground_truth()
    results: dict = {}
    total_tp = total_pred = total_gt = 0

    for fname in sorted(gt_all):
        if files and fname not in files:
            continue
        path = SPECIMEN_DIR / fname
        if not path.exists():
            results[fname] = {"error": "file not found"}
            continue

        grid, _ = read_specimen(path)
        gt_bag = long_rows(grid, gt_all[fname])

        try:
            regions = detect(grid)
            pred_models = [build_table_model(grid, r) for r in regions]
        except Exception as e:
            pred_models = []
            results[fname] = {"error": f"detect failed: {e}"}
        pred_bag = long_rows(grid, pred_models)

        s = score_file(pred_bag, gt_bag)
        s["n_tables_pred"] = len(pred_models)
        s["n_tables_gt"] = len(gt_all[fname])
        results[fname] = s

        total_tp += s["tp"]
        total_pred += s["pred"]
        total_gt += s["gt"]

    file_scores = [r for r in results.values() if "f1" in r]
    micro_p = total_tp / total_pred if total_pred else 0.0
    micro_r = total_tp / total_gt if total_gt else 0.0
    micro_f1 = (2 * micro_p * micro_r / (micro_p + micro_r)
                if (micro_p + micro_r) > 0 else 0.0)
    macro_f1 = (sum(r["f1"] for r in file_scores) / len(file_scores)
                if file_scores else 0.0)
    perfect = sum(1 for r in file_scores if r["f1"] >= 0.999)

    results["_aggregate"] = {
        "files": len(file_scores),
        "perfect_files": perfect,
        "micro_precision": round(micro_p, 4),
        "micro_recall": round(micro_r, 4),
        "micro_f1": round(micro_f1, 4),
        "macro_f1": round(macro_f1, 4),
    }

    if verbose:
        print(f"{'file':<45} {'P':>7} {'R':>7} {'F1':>7}  tables(p/g)")
        print("-" * 80)
        for fname in sorted(k for k in results if not k.startswith("_")):
            r = results[fname]
            if "f1" in r:
                print(f"{fname:<45} {r['precision']:>7.3f} {r['recall']:>7.3f} "
                      f"{r['f1']:>7.3f}  {r['n_tables_pred']}/{r['n_tables_gt']}")
            else:
                print(f"{fname:<45} ERROR: {r.get('error')}")
        agg = results["_aggregate"]
        print("-" * 80)
        print(f"micro P/R/F1: {agg['micro_precision']:.4f} / "
              f"{agg['micro_recall']:.4f} / {agg['micro_f1']:.4f}   "
              f"macro F1: {agg['macro_f1']:.4f}   "
              f"perfect: {agg['perfect_files']}/{agg['files']}")

    return results


if __name__ == "__main__":
    only = sys.argv[1:] or None
    res = evaluate(only)
    RESULTS_PATH.write_text(
        json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nresults written to {RESULTS_PATH}")
