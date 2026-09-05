#!/usr/bin/env python3
"""Label-free context-budget preflight for the active Track-B prompts.

The preflight never calls an LLM and never reads mutation/gold assets.  It renders the
same full selector and probe-generator prompts used by Track B, measures them against
the explicitly requested Ollama context window, and stops the run before evaluated
calls if any known prompt cannot fit.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable, List

import probe_engine as pe
import problem_metadata as pmeta
import requirement_provider as rp
import runtime_context as rctx
import track_b


FIELDS = (
    "candidate_id", "problem_id", "requirement_id", "stage",
    "prompt_character_count", "prompt_utf8_bytes",
    "estimated_prompt_tokens", "requested_num_predict", "safety_tokens",
    "requested_num_ctx", "required_context_tokens", "context_headroom_tokens",
    "context_budget_safe", "token_estimator",
)


def build_rows(candidates: Iterable[Dict[str, Any]], provider: rp.RequirementProvider,
               project_root: Path, *, num_ctx: int, probe_num_predict: int,
               safety_tokens: int) -> List[Dict[str, Any]]:
    """Render every known full Track-B selector/generator prompt without model calls."""
    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        pid = int(candidate["problem_id"])
        code = (project_root / candidate["code_path"]).read_text(encoding="utf-8")
        payload = rp.build_candidate_prompt_payload(provider, pid, code)
        inventory = pe.introspect(code, dict(payload.get("data_instance", {})))
        if "error" in inventory:
            raise RuntimeError(
                f"context preflight could not introspect {candidate['candidate_id']}: "
                f"{inventory['error']}")
        problem = dict(provider.problem(pid))
        problem.setdefault("problem_type", payload.get("problem_type", ""))
        problem.setdefault("question", payload.get("problem_description", ""))
        problem.setdefault("problem_description", payload.get("problem_description", ""))
        problem.setdefault("data_instance", payload.get("data_instance", {}))
        for requirement in payload["requirements"]:
            rid = str(requirement["requirement_id"])
            allowed = pe.compatible_templates(requirement)
            metadata = pmeta.build_metadata(problem, requirement, allowed)
            pmeta.assert_no_oracle_fields(metadata)
            slice_ = pe.requirement_inventory_slice(
                inventory, requirement, dict(payload.get("data_instance", {})))
            prompts = (
                ("template_selector", track_b._selector_prompt(
                    payload, requirement, slice_, allowed, metadata, []), 600),
                ("probe_generator", track_b._probe_prompt(
                    payload, requirement, slice_, allowed, metadata), probe_num_predict),
            )
            for stage, prompt, output_tokens in prompts:
                budget = rctx.budget_record(
                    prompt, num_predict=int(output_tokens), num_ctx=int(num_ctx),
                    safety_tokens=int(safety_tokens))
                rows.append({
                    "candidate_id": candidate["candidate_id"],
                    "problem_id": pid,
                    "requirement_id": rid,
                    "stage": stage,
                    **budget,
                })
    return rows


def write_report(rows: Iterable[Dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def assert_all_safe(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(rows)
    unsafe = [row for row in rows if not row["context_budget_safe"]]
    largest = max(
        rows, key=lambda row: int(row["required_context_tokens"]), default=None)
    if unsafe:
        first = unsafe[0]
        raise rctx.ContextBudgetError(
            "context preflight failed before evaluated calls: "
            f"{len(unsafe)} rendered prompt(s) exceed num_ctx; first="
            f"{first['candidate_id']}/{first['requirement_id']}/{first['stage']} "
            f"requires {first['required_context_tokens']} tokens but num_ctx="
            f"{first['requested_num_ctx']}. Full prompts were preserved.")
    return {
        "rendered_prompt_count": len(rows),
        "unsafe_prompt_count": 0,
        "largest_known_prompt": largest or {},
    }
