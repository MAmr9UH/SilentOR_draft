#!/usr/bin/env python3
"""Run the retained V42 probe-aware Experiment 2 pipeline.

This runner reads only the label-free candidate registry and canonical visible problem assets.
Hidden mutant labels are used only by the offline diagnosis scorer.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable

import context_preflight as cpreflight
import common_runner as cr
import experiment_configs as expcfg
import freeze_manifest
import requirement_provider as rp
import runtime_context as rctx
import shadow_witness_architecture as swa
import track_b

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "candidate_registry.json"
FINAL_VERDICTS = ("correct", "incorrect", "pipeline_error")


def load_candidates() -> list[dict]:
    root = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if root.get("schema_version") != 1:
        raise ValueError("unsupported candidate registry schema")
    rows = root.get("candidates", [])
    required = {"candidate_id", "candidate_kind", "problem_id", "code_path"}
    seen = set()
    for row in rows:
        if set(row) != required:
            raise ValueError(f"invalid candidate registry entry: {row.get('candidate_id')}")
        if row["candidate_id"] in seen:
            raise ValueError(f"duplicate candidate_id {row['candidate_id']}")
        seen.add(row["candidate_id"])
        if not (HERE / row["code_path"]).is_file():
            raise FileNotFoundError(HERE / row["code_path"])
    return rows


def validate_full_candidate_design(rows: Iterable[dict]) -> dict:
    rows = list(rows)
    bases = [row for row in rows if row["candidate_kind"] == "base"]
    mutants = [row for row in rows if row["candidate_kind"] == "mutant"]
    if len(rows) != 111 or len(bases) != 29 or len(mutants) != 82:
        raise ValueError(
            f"expected frozen 111-candidate design (29 bases, 82 mutants), got "
            f"{len(rows)}, {len(bases)}, {len(mutants)}")
    base_pids = [int(row["problem_id"]) for row in bases]
    if len(set(base_pids)) != 29:
        raise ValueError("expected exactly one base per EXP2 problem")
    if {int(row["problem_id"]) for row in mutants} != set(base_pids):
        raise ValueError("mutant and base problem sets differ")
    return {"candidates": 111, "bases": 29, "mutants": 82, "problems": 29}


def _result_row(candidate: dict, prediction: dict, accounting: dict,
                *, model: str, repetition: int, seed: int) -> Dict[str, Any]:
    verdict = str(prediction.get("verdict", "pipeline_error"))
    if verdict not in FINAL_VERDICTS:
        raise ValueError(f"forbidden final verdict {verdict!r}")
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_kind": candidate["candidate_kind"],
        "problem_id": int(candidate["problem_id"]),
        "track": "B", "architecture": swa.ARCHITECTURE_NAME,
        "model": model, "repetition": repetition, "seed": seed,
        "verdict": verdict,
        "suspected_requirement_ids": json.dumps(
            prediction.get("suspected_requirement_ids", []), separators=(",", ":")),
        "primary_suspected_requirement_id":
            prediction.get("primary_suspected_requirement_id") or "",
        "predicted_taxonomy_category":
            prediction.get("predicted_taxonomy_category", "none"),
        "prediction_valid": bool(accounting.get("prediction_valid", False)),
        "validation_errors": accounting.get("validation_errors", ""),
        "pipeline_error_count": int(accounting.get("pipeline_error_count", 0)),
        "unresolved_requirement_count": int(
            accounting.get("unresolved_requirement_count", 0)),
        "evaluation_complete": bool(accounting.get("evaluation_complete", False)),
        "probes_generated": int(accounting.get("probes_generated", 0)),
        "probes_valid": int(accounting.get("probes_valid", 0)),
        "probes_executed": int(accounting.get("probes_executed", 0)),
        "solver_calls": int(accounting.get("solver_calls", 0)),
        "input_tokens": int(accounting.get("input_tokens", 0)),
        "output_tokens": int(accounting.get("output_tokens", 0)),
        "runtime_sec": accounting.get("runtime_sec", 0.0),
        "witness_probe_aware_call_count": int(
            accounting.get("witness_probe_aware_call_count", 0)),
        "root_cause_call_count": int(accounting.get("root_cause_call_count", 0)),
    }


def _append_csv(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def run(args: argparse.Namespace) -> None:
    freeze_problems = freeze_manifest.verify()
    if freeze_problems:
        raise RuntimeError(
            "freeze manifest drift:\n  - " + "\n  - ".join(freeze_problems))
    candidates = load_candidates()
    if not args.smoke:
        validate_full_candidate_design(candidates)
    if args.candidate_id:
        candidates = [row for row in candidates if row["candidate_id"] == args.candidate_id]
        if not candidates:
            raise ValueError(f"unknown candidate_id {args.candidate_id}")
    elif args.smoke:
        candidates = candidates[:1]

    provider = rp.RequirementProvider()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Retain the original V42 fail-fast context checks inside the runner. These are
    # initialization diagnostics only: they do not call an LLM or change any probe,
    # requirement, route, verifier decision, or candidate verdict.
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    if cr.infer_provider(args.model) == "ollama":
        runtime_check = rctx.verify_requested_context(
            args.ollama_url, args.model, int(args.ollama_num_ctx))
        (diagnostics / "context_runtime_verification.json").write_text(
            json.dumps([runtime_check], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        preflight_rows = cpreflight.build_rows(
            candidates, provider, HERE, num_ctx=int(args.ollama_num_ctx),
            probe_num_predict=int(args.probe_num_predict),
            safety_tokens=int(args.context_safety_tokens))
        cpreflight.write_report(
            preflight_rows, diagnostics / "context_preflight.csv")
        preflight_summary = cpreflight.assert_all_safe(preflight_rows)
        (diagnostics / "context_preflight_summary.json").write_text(
            json.dumps(preflight_summary, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8")
        print(
            f"[context preflight] safe={preflight_summary['rendered_prompt_count']} "
            f"num_ctx={args.ollama_num_ctx} full_prompts_preserved=True",
            flush=True)
    for repetition in range(1, args.repetitions + 1):
        for candidate in candidates:
            pid = int(candidate["problem_id"])
            problem = provider.problem(pid)
            code = (HERE / candidate["code_path"]).read_text(encoding="utf-8")
            payload = rp.build_candidate_prompt_payload(provider, pid, code)
            started = time.time()
            try:
                prediction, accounting = track_b.verify(
                    payload, args.model, problem_record=problem,
                    temperature=args.temperature, seed=args.seed,
                    ollama_url=args.ollama_url, candidate_id=candidate["candidate_id"],
                    ollama_num_ctx=args.ollama_num_ctx,
                    require_think_disabled=not args.allow_think_fallback,
                    context_safety_tokens=args.context_safety_tokens,
                    probe_num_predict=args.probe_num_predict,
                    semantic_num_predict=args.semantic_num_predict,
                    witness_verifier_num_predict=args.witness_verifier_num_predict,
                    root_cause_num_predict=args.root_cause_num_predict,
                    judge_panel=args.judge_panel,
                    semantic_validation_mode=args.semantic_validation_mode,
                    attempt_record_path=out / "attempt_records" /
                        f"{candidate['candidate_id']}.jsonl")
            except rctx.ContextBudgetError:
                raise
            except Exception as exc:
                prediction = {
                    "verdict": "pipeline_error", "suspected_requirement_ids": [],
                    "primary_suspected_requirement_id": None,
                    "predicted_taxonomy_category": "none", "error_reason": str(exc),
                    "evidence": "", "confidence": 0.0,
                }
                accounting = track_b._blank_accounting(
                    f"{type(exc).__name__}: {exc}",
                    semantic_validation_mode=args.semantic_validation_mode)
            accounting["runtime_sec"] = round(time.time() - started, 3)
            row = _result_row(candidate, prediction, accounting, model=args.model,
                              repetition=repetition, seed=args.seed)
            _append_csv(out / "results.csv", row)
            with (out / "raw.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"result": row, "prediction": prediction,
                                         "accounting": accounting}, default=str) + "\n")
            print(json.dumps(row, default=str), flush=True)
            print(swa.format_live_verification(accounting), flush=True)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", default="track_b")
    p.add_argument("--model", default="gemma3:12b")
    p.add_argument("--repetitions", type=int, default=1)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--out", default="runs/v42_probe_aware_root")
    p.add_argument("--candidate-id")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--ollama-url", default="http://localhost:11434/api/generate")
    p.add_argument("--ollama-num-ctx", type=int, default=40960)
    p.add_argument("--context-safety-tokens", type=int, default=1024)
    p.add_argument("--probe-num-predict", type=int, default=4000)
    p.add_argument("--semantic-num-predict", type=int, default=4800)
    p.add_argument("--witness-verifier-num-predict", type=int, default=2400)
    p.add_argument("--root-cause-num-predict", type=int, default=2400)
    p.add_argument("--judge-panel", default="B_all_llm")
    p.add_argument("--semantic-validation-mode", choices=("enforce", "log-only", "off"),
                   default="enforce")
    p.add_argument("--allow-think-fallback", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    cfg = expcfg.load_config(args.config)
    for key, value in cfg.items():
        attr = key.replace("-", "_")
        if hasattr(args, attr) and parser().get_default(attr) == getattr(args, attr):
            setattr(args, attr, value)
    run(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
