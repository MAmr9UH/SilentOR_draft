#!/usr/bin/env python3
"""Offline diagnosis-only SILENT EXACT LOCALIZATION scorer.

This module never participates in candidate verdicts, probe routing, generation, validation,
execution, witness verification, or root-cause adjudication.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "mutants" / "MUTANT_MANIFEST.json"


def _gold_silent() -> dict[str, str]:
    root = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = root.get("certified_silent", [])
    return {str(row["candidate_id"]): str(row["injected_requirement"]) for row in rows}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def score(rows: list[dict[str, Any]], *, historical_projection: bool = False) -> dict:
    if historical_projection and rows and "policy" in rows[0]:
        matches = [row for row in rows if row.get("policy") == "probe_aware_root"]
        if len(matches) != 1:
            raise ValueError("historical score table lacks a unique probe_aware_root row")
        row = matches[0]
        exact = int(row["silent_primary_exact_count"])
        total = int(row["silent_mutant_n"])
        return {
            "metric": "SILENT EXACT LOCALIZATION",
            "diagnosis_only": True,
            "affects_candidate_verdicts_or_probe_decisions": False,
            "historical_aggregate": True,
            "policy": "probe_aware_root",
            "exact": exact, "eligible_silent_mutants": total,
            "rate": exact / total if total else None, "details": [],
        }
    gold = _gold_silent()
    details = []
    for row in rows:
        cid = str(row.get("candidate_id", ""))
        if cid not in gold:
            continue
        if historical_projection:
            verdict = str(row.get("shadow_probe_aware_verdict", ""))
            primary = str(row.get("shadow_probe_aware_root_primary", ""))
        else:
            verdict = str(row.get("verdict", ""))
            primary = str(row.get("primary_suspected_requirement_id", ""))
        exact = verdict.lower() == "incorrect" and primary == gold[cid]
        details.append({
            "candidate_id": cid, "expected_requirement_id": gold[cid],
            "verdict": verdict, "predicted_primary_requirement_id": primary,
            "silent_exact_localization": exact,
        })
    total = len(details)
    exact = sum(int(row["silent_exact_localization"]) for row in details)
    return {
        "metric": "SILENT EXACT LOCALIZATION",
        "diagnosis_only": True,
        "affects_candidate_verdicts_or_probe_decisions": False,
        "exact": exact, "eligible_silent_mutants": total,
        "rate": exact / total if total else None,
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, nargs="?")
    parser.add_argument("--historical-policy-scores", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reports/silent_exact_localization.json"))
    args = parser.parse_args()
    source = args.historical_policy_scores or args.results
    if source is None:
        parser.error("provide results.csv or --historical-policy-scores FILE")
    report = score(_load_rows(source), historical_projection=bool(args.historical_policy_scores))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"SILENT EXACT LOCALIZATION: {report['exact']}/{report['eligible_silent_mutants']} "
          f"({100.0 * report['rate']:.2f}%)" if report["rate"] is not None else
          "SILENT EXACT LOCALIZATION: no eligible rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
