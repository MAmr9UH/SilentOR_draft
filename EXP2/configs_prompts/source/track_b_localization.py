#!/usr/bin/env python3
"""Deterministic localization for Track B.

Evidence authority is a hard primary-ranking constraint:

1. complete metadata-scoped declared-attribute mismatch;
2. other direct deterministic structural mismatch;
3. valid executable failure;
4. partial or unresolved evidence;
5. unresolved evidence.

Within a tier, the original v12 causal tie-breaking remains unchanged.

Track B probes every requirement independently and, before v12, reported EVERY probe-FAIL in
``suspected_requirement_ids``.  Under the single-fault mutant design at most one requirement
is genuinely mis-modelled, so a mutation that shifts the optimum can make unrelated
requirements' probes fail too (collateral fails).  The forensic replay of r0 showed 100% of
the 155 extra suspected IDs originated from real, valid probe-FAILs -- not fallback -- so the
fix belongs at AGGREGATION, not in probe generation.

This module adds two deterministic, manifest-free steps applied AFTER all probes have run and
BEFORE the prediction is assembled.  Neither changes the candidate-level verdict: the verdict
stays ``incorrect`` iff at least one trusted probe failed.

  1. root_cause_isolation(): partition the failed requirements into ROOT-CAUSE candidates and
     likely-COLLATERAL fails using only the recorded probe evidence (residual magnitude vs the
     probe's own acceptance margin, relation locality, and semantic-alignment status).  A fail
     whose violation is barely past its margin AND whose relation touches many variables is
     treated as collateral evidence, not a primary suspect.  All failed IDs are still preserved
     for audit.

  2. select_primary(): choose ONE ``primary_suspected_requirement_id`` from the root-cause set
     with a frozen deterministic ranking: exact semantic alignment > validated direct witness
     > relation locality (fewer variables = more specific) > larger margin-normalised residual
     > stable lexical tie-break.  No hidden-manifest / target information is ever consulted.

The scoring keys are intentionally simple, monotone, and fully recorded so the choice is
auditable and reproducible.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import structural_evidence as structural_rules

# A fail is treated as a strong root-cause candidate when its recomputed violation exceeds its
# own acceptance margin by at least this factor.  Near-margin fails (just past tolerance) are
# the signature of an optimum that drifted because of a DIFFERENT requirement's fault.
ROOT_CAUSE_MARGIN_MULTIPLE = 10.0
# Relations touching more than this many distinct variables are "broad": a broad relation that
# fails only marginally is weak localization evidence.
BROAD_RELATION_VARS = 6


def _fail_entries(probe_log: List[Dict[str, Any]],
                  result_labels: Dict[str, str]) -> List[Dict[str, Any]]:
    fails = []
    for entry in probe_log:
        rid = str(entry.get("requirement_id", ""))
        if result_labels.get(rid) in (
                "PROBE_FAIL", "STRUCTURAL_FAIL"):
            fails.append(entry)
    return fails


def _residual_and_margin(entry: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    result = entry.get("execution_result") or entry.get("tier1") or {}
    residual = result.get("recomputed_violation")
    margin = result.get("acceptance_margin")
    if residual is None:
        for test in result.get("tests", []) or []:
            if isinstance(test, dict) and test.get("status") == "WITNESS_FOUND":
                residual = test.get("recomputed_violation", test.get("violation_value"))
                if margin is None:
                    margin = test.get("acceptance_margin")
                break
    try:
        residual = float(residual) if residual is not None else None
    except (TypeError, ValueError):
        residual = None
    try:
        margin = float(margin) if margin is not None else None
    except (TypeError, ValueError):
        margin = None
    return residual, margin


def _relation_var_count(entry: Dict[str, Any]) -> int:
    probe = entry.get("normalized_probe") or {}
    params = probe.get("parameters", {}) if isinstance(probe, dict) else {}
    names = set()
    structural = entry.get("structural_evidence") or entry.get("tier1") or {}
    for value in structural.get("target_variables", []) or []:
        names.add(str(value.get("name", "")) if isinstance(value, dict) else str(value))
    for key in ("target_variables", "lhs_terms"):
        for item in params.get(key, []) or []:
            if isinstance(item, dict):
                names.add(str(item.get("symbol", item.get("var", ""))))
            else:
                names.add(str(item))
    for side in ("antecedent", "consequent"):
        for relation in params.get(side, []) or []:
            for term in (relation.get("lhs_terms", []) if isinstance(relation, dict) else []):
                names.add(str(term.get("symbol", term.get("var", ""))))
    names.discard("")
    return len(names)


def _alignment_confirmed(entry: Dict[str, Any]) -> bool:
    alignment = entry.get("semantic_alignment")
    if isinstance(alignment, dict):
        return str(alignment.get("status", "")).upper() == "CONFIRMED"
    return False


def _witness_validated(entry: Dict[str, Any]) -> bool:
    result = entry.get("execution_result") or {}
    if str(result.get("witness_status", "")).upper() in ("WITNESS_FOUND", "VALIDATED"):
        return True
    replay = result.get("full_model_replay")
    return isinstance(replay, dict) and replay.get("feasible") is True


def _is_structural(entry: Dict[str, Any]) -> bool:
    probe = entry.get("normalized_probe") or {}
    result = entry.get("execution_result") or {}
    return (
        str(probe.get("probe_template", "")) == "check_variable_property" and
        str(result.get("structural_status", "")) != "REQUIRES_SOLVER")


def _authoritative_declared_attribute(entry: Dict[str, Any]) -> bool:
    structural = entry.get("structural_evidence") or entry.get("tier1") or {}
    return bool(
        (str(entry.get("decision_source", "")) == "structural_witness" or
         _is_structural(entry)) and
        structural_rules.is_authoritative_declared_attribute_failure(structural)
    )


def _evidence_tier(entry: Dict[str, Any], *, structural: bool,
                   probe_witness: bool) -> int:
    if _authoritative_declared_attribute(entry):
        return 1
    if structural:
        return 2
    if probe_witness:
        return 3
    return 4


def classify_fail(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Return an auditable evidence record + a root_cause flag for one failed requirement."""
    residual, margin = _residual_and_margin(entry)
    var_count = _relation_var_count(entry)
    aligned = _alignment_confirmed(entry)
    witness = _witness_validated(entry)
    source = str(entry.get("decision_source", ""))
    structural = source == "structural_witness" or _is_structural(entry)
    probe_witness = source == "probe_witness" or entry.get("result_label") == "PROBE_FAIL"
    authoritative = _authoritative_declared_attribute(entry)
    evidence_tier = _evidence_tier(
        entry, structural=structural, probe_witness=probe_witness)

    # margin-normalised residual: how many margins past tolerance the violation is.
    if residual is not None and margin is not None and margin > 0:
        margin_multiple = residual / margin
    elif residual is not None:
        margin_multiple = residual
    else:
        margin_multiple = None

    strong_violation = (margin_multiple is None or
                        margin_multiple >= ROOT_CAUSE_MARGIN_MULTIPLE)
    broad = var_count > BROAD_RELATION_VARS

    # Root cause unless it looks collateral: a broad relation failing only marginally is the
    # collateral signature.  Structural (domain) fails and alignment-confirmed fails are always
    # root-cause candidates -- a variable's own domain cannot fail as a side effect of another
    # requirement's fault.  Fallback fails are always kept (no probe evidence to down-weight).
    collateral = broad and not strong_violation and not structural and not aligned
    root_cause = not collateral

    return {
        "requirement_id": str(entry.get("requirement_id", "")),
        "result_label": entry.get("result_label"),
        "residual": residual, "acceptance_margin": margin,
        "margin_multiple": margin_multiple, "relation_variables": var_count,
        "semantic_alignment_confirmed": aligned, "witness_validated": witness,
        "structural": structural,
        "authoritative_declared_attribute": authoritative,
        "declared_attribute": (entry.get("structural_evidence") or
                               entry.get("tier1") or {}).get("declared_attribute"),
        "evidence_tier": evidence_tier,
        "probe_witness": probe_witness,
        "strong_violation": strong_violation, "broad_relation": broad,
        "root_cause_candidate": root_cause,
        "collateral_reason": "" if root_cause else
        "broad relation with near-margin residual and no confirmed alignment (likely "
        "collateral to another requirement's fault)",
    }


def _primary_sort_key(record: Dict[str, Any]):
    """Frozen deterministic ranking (higher tuple = better primary). Never uses target info."""
    margin_multiple = record.get("margin_multiple")
    margin_rank = margin_multiple if isinstance(margin_multiple, (int, float)) else 0.0
    tier = int(record.get("evidence_tier", 5) or 5)
    # Evidence subtype remains only a same-tier tie-break, preserving the pre-v42 ordering where
    # possible.  It can never move a lower-authority tier above a higher-authority tier.
    subtype_rank = (
        3 if record.get("probe_witness") else
        1 if record.get("structural") else
        0
    )
    return (
        -tier,
        subtype_rank,
        1 if record.get("semantic_alignment_confirmed") else 0,
        1 if record.get("witness_validated") else 0,
        1 if record.get("authoritative_declared_attribute") else 0,
        1 if record.get("structural") else 0,
        -record.get("relation_variables", 999),
        margin_rank,
    )


def localize(probe_log: List[Dict[str, Any]],
             result_labels: Dict[str, str]) -> Dict[str, Any]:
    """Compute preserved fail IDs, per-fail evidence, the root-cause subset, and the single
    deterministic primary suspect.  Verdict logic is untouched.

    Root-cause isolation reuses evidence ALREADY recorded by each probe (recomputed residual,
    the probe's own acceptance margin, full-model witness replay, semantic alignment, relation
    locality).  It adds NO solver calls and NO LLM calls, so Track B's detection recall, base
    false-positive rate, and solver-call count are unchanged by construction; only the
    reported localization fields change.
    """
    fails = _fail_entries(probe_log, result_labels)
    records = [classify_fail(entry) for entry in fails]
    all_fail_ids = [record["requirement_id"] for record in records]
    root_records = [record for record in records if record["root_cause_candidate"]]
    pool = root_records or records  # never empty when there is at least one fail
    ranked = sorted(pool, key=lambda record: (_primary_sort_key(record),
                                              # lexical tie-break: smaller id first
                                              tuple(-ord(character)
                                                    for character in record["requirement_id"])),
                    reverse=True)
    primary = ranked[0]["requirement_id"] if ranked else None
    ranked_ids = [record["requirement_id"] for record in ranked]
    collateral_records = [
        record for record in records if not record["root_cause_candidate"]
    ]
    collateral_ranked = sorted(
        collateral_records,
        key=lambda record: (_primary_sort_key(record),
                            tuple(-ord(character)
                                  for character in record["requirement_id"])),
        reverse=True)
    ranked_ids.extend(
        record["requirement_id"] for record in collateral_ranked
        if record["requirement_id"] not in ranked_ids)
    return {
        "all_failed_requirement_ids": all_fail_ids,
        "root_cause_requirement_ids": [record["requirement_id"] for record in root_records],
        "collateral_requirement_ids": [record["requirement_id"] for record in records
                                       if not record["root_cause_candidate"]],
        "primary_suspected_requirement_id": primary,
        "ranked_requirement_ids": ranked_ids,
        "localization_evidence": records,
    }
