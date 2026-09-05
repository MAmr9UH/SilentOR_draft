#!/usr/bin/env python3
"""Human-readable, one-file-per-problem reports for the retained V42 pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str)


def _status(record: Dict[str, Any]) -> str:
    compiler = record.get("compiler_result") or {}
    validator = record.get("validator_result") or {}
    execution = record.get("execution_result") or {}
    route = str(record.get("final_route", ""))
    if compiler.get("status") == "NOT_PROBEABLE" or route == "compiler_rejected":
        return "Compiler rejected"
    if route in {"conservation_semantic_repair", "validator_blocked"} or (
            validator.get("ok") is False and validator.get("reason") not in {"not_run", ""}):
        return "Semantic validator rejected"
    if route in {"judges_1_2_repair", "judge_3_repair", "not_approved_repair_requested"}:
        return "Judge requested repair"
    if record.get("execution_mode") == "diagnostic_only":
        return "Diagnostic only"
    if execution:
        return "Executed"
    if "technical" in route:
        return "Technical failure"
    return route.replace("_", " ").title() or "Not run"


def _reason(record: Dict[str, Any]) -> str:
    compiler = record.get("compiler_result") or {}
    validator = record.get("validator_result") or {}
    if compiler.get("status") == "NOT_PROBEABLE":
        return str(compiler.get("reason", "compiler rejected"))
    if validator.get("ok") is False and validator.get("reason") not in {"not_run", ""}:
        return str(validator.get("reason"))
    findings = []
    for judge in record.get("judge_decisions", []) or []:
        if judge.get("verdict") == "REPAIR":
            detail = judge.get("reason")
            if detail:
                findings.append(str(detail))
    if findings:
        return " | ".join(dict.fromkeys(findings))
    execution = record.get("execution_result") or {}
    return str(execution.get("message") or record.get("final_route") or "")


def _summary_counts(records: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {
        "Total probe attempts": 0,
        "Executed": 0,
        "Compiler rejected": 0,
        "Semantic validator rejected": 0,
        "Judge requested repair": 0,
        "Diagnostic only (WARNING)": 0,
        "Technical failure": 0,
    }
    for record in records:
        counts["Total probe attempts"] += 1
        status = _status(record)
        mapping = {
            "Executed": "Executed",
            "Compiler rejected": "Compiler rejected",
            "Semantic validator rejected": "Semantic validator rejected",
            "Judge requested repair": "Judge requested repair",
            "Diagnostic only": "Diagnostic only (WARNING)",
            "Technical failure": "Technical failure",
        }
        if status in mapping:
            counts[mapping[status]] += 1
    return counts


def _run_section(*, run_key: str, candidate_id: str,
                 requirements: List[Dict[str, Any]],
                 attempts: List[Dict[str, Any]],
                 probe_aware_records: Dict[str, Dict[str, Any]],
                 root_cause_record: Dict[str, Any]) -> str:
    requirement_by_id = {str(item.get("requirement_id")): item for item in requirements}
    attempts_by_id: Dict[str, List[Dict[str, Any]]] = {}
    for record in attempts:
        attempts_by_id.setdefault(str(record.get("requirement_id", "")), []).append(record)
    counts = _summary_counts(attempts)
    lines = [f"<!-- RUN {run_key} START -->", f"# Candidate `{candidate_id}`", "", "## Summary", "",
             f"- Total requirements: {len(requirements)}"]
    lines.extend(f"- {name}: {value}" for name, value in counts.items())
    lines.extend(["", "---", ""])
    for rid, requirement in requirement_by_id.items():
        lines.extend([
            f"## Requirement `{rid}`", "", "**Requirement**", "",
            f"> {requirement.get('requirement_text', '')}", "", "**Category**", "",
            str(requirement.get("category", "")), "",
        ])
        records = attempts_by_id.get(rid, [])
        if not records:
            lines.extend(["_No generated probe attempt._", "", "---", ""])
            continue
        for number, record in enumerate(records, start=1):
            lines.extend([
                f"### Attempt {record.get('attempt', number)}", "",
                f"**Status:** {_status(record)}", "", "**Reason**", "",
                _reason(record) or "No additional reason recorded.", "",
            ])
            judges = record.get("judge_decisions") or []
            if judges:
                lines.extend(["**Votes**", ""])
                for judge in judges:
                    lines.append(f"- {judge.get('judge', 'judge')}: {judge.get('verdict', 'NOT_RUN')}")
                lines.append("")
            for label, key in (
                    ("Raw generated probe", "raw_generated_probe"),
                    ("Generated typed probe", "typed_probe"),
                    ("Compiled executable probe", "compiled_probe")):
                value = record.get(key)
                if value is not None:
                    lines.extend([f"**{label}**", "", "```json", _json(value), "```", ""])
            log_only = record.get("semantic_validator_log_only")
            if log_only:
                lines.extend(["**Semantic validator log-only measurement**", "", "```json",
                              _json(log_only), "```", ""])
            execution = record.get("execution_result")
            if execution is not None:
                lines.extend([
                    "**Solver result**", "", str(execution.get("status", "UNKNOWN")), "",
                    "```json", _json(execution), "```", "",
                ])
        if rid in probe_aware_records:
            lines.extend(["### Witness verification detail", ""])
            value = probe_aware_records.get(rid)
            lines.extend(["**Probe-aware verifier**", "", "```json",
                          _json(value), "```", ""])
        lines.extend(["---", ""])
    if root_cause_record:
        lines.extend(["## Root-cause adjudication", "", "```json",
                      _json(root_cause_record), "```", ""])
    lines.append(f"<!-- RUN {run_key} END -->")
    return "\n".join(lines) + "\n"


def write_problem_report(*, output_dir: Path, problem_id: Any, run_key: str,
                         candidate_id: str, requirements: List[Dict[str, Any]],
                         attempts: List[Dict[str, Any]],
                         probe_aware_records: Dict[str, Dict[str, Any]],
                         root_cause_record: Dict[str, Any]) -> Path:
    folder = Path(output_dir) / "probe_forensics"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"p{problem_id}.md"
    start = f"<!-- RUN {run_key} START -->"
    end = f"<!-- RUN {run_key} END -->"
    old = path.read_text(encoding="utf-8") if path.exists() else f"# Problem p{problem_id}\n\n"
    section = _run_section(
        run_key=run_key, candidate_id=candidate_id, requirements=requirements,
        attempts=attempts, probe_aware_records=probe_aware_records,
        root_cause_record=root_cause_record)
    if start in old and end in old:
        before = old.split(start, 1)[0]
        after = old.split(end, 1)[1].lstrip("\n")
        text = before + section + ("\n" + after if after else "")
    else:
        text = old.rstrip() + "\n\n" + section
    path.write_text(text, encoding="utf-8")
    return path
