#!/usr/bin/env python3
"""Probe-aware witness filtering and root-cause adjudication for V42.

* The operations-research expert sees the evidence plus the exact normalized probe.
* The root-cause adjudicator receives only requirements whose witnesses the verifier confirmed,
  their certificates, and deterministic comparison features.

Neither role receives judge votes, mutation labels, hidden answers, or gold artifacts.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from itertools import combinations
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


ROLE_WITNESS_VERIFIER = "probe-aware operations-research witness verifier"
ROLE_ROOT_CAUSE_ADJUDICATOR = "shadow root-cause adjudicator"

YES = "YES"
NO = "NO"
VERIFIER_DECISIONS = frozenset({YES, NO})
WITNESS_V_REJECT = "WITNESS_V_REJECT"
RANKED = "RANKED"
ROOT_DECISIONS = frozenset({RANKED})

ARCHITECTURE_NAME = "probe_aware_root"
CERTIFICATE_VERSION = 4
MAX_TECHNICAL_RETRIES = 3


WITNESS_VERIFIER_PROMPT = """ROLE: Operations-research witness verifier.

Answer exactly one question:
Do the supplied concrete facts, interpreted through the exact generated probe, prove that the
written requirement is violated?

Use only:
- the written requirement;
- the visible problem data;
- the variable meanings;
- the measured facts and supplied certificate;
- the exact normalized generated probe.

YOUR TASK:
1. State what the requirement demands.
2. Check whether the generated probe represents that requirement faithfully.
3. Decide whether the concrete facts prove a violation of the written requirement.

DECISION MEANINGS:
- YES: the visible facts and faithful probe are sufficient to prove a violation.
- NO: the supplied witness does not establish a violation of the original requirement.

IMPORTANT:
- Candidate-model feasibility does not itself prove requirement satisfaction.
- Inspect the exact generated probe, but do not invent a replacement probe.
- If the probe changes the requirement's variables, operator, aggregation, scope, index coverage,
  coefficient, threshold, or property, return NO.
- Do not see or infer another verifier's answer or any judge vote.
- Do not invent values, properties, relationships, indices, or assumptions.
- For indexed requirements, do not infer unobserved indices.
- Treat -0.0 as exactly 0.0.
- Missing or malformed evidence and technical failures are handled outside this semantic decision;
  do not invent a YES or NO when the supplied input cannot be evaluated.

VISIBLE_INPUT:
{visible_input}

Return only valid JSON:
{{"requirement_demands":"direction, aggregation, scope, and threshold",
  "decisive_check":"the exact comparison or missing fact",
  "reason":"one short sentence grounded in the requirement",
  "decision":"YES|NO"}}
"""

ROOT_CAUSE_PROMPT = """ROLE: shadow root-cause adjudicator.

Several requirement-specific failures were independently confirmed as real violations.
Rank EVERY supplied failed requirement from most likely original modeling fault to most likely
collateral consequence. You must return every supplied requirement exactly once. You cannot
abstain. Use the requirement texts, certificates, and deterministic comparison features.
The supplied evidence_authority_tier is a hard ordering constraint: every lower-numbered tier must
appear before every higher-numbered tier. Rank causal likelihood only within the same tier.
Do not use list order as evidence. Margins with different units are not directly comparable unless
the supplied normalized values justify comparison.

VISIBLE_INPUT:
{visible_input}

Return only:
{{"decision":"RANKED",
  "primary_requirement_id":"the first supplied ID in your ranking",
  "ranked_requirement_ids":["all supplied IDs, most likely first"],
  "collateral_requirement_ids":["zero or more supplied IDs"],
  "reason":"short evidence-grounded explanation"}}
"""


CallJSON = Callable[[str, Optional[int], int],
                    Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]]


def _clean_number(value: Any) -> Any:
    """Normalize finite numbers, including the display-only negative-zero artifact."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            return None
        return 0.0 if number == 0.0 else number
    return value


def _json_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _variable_map(inventory: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item.get("name", "")): {
            "name": str(item.get("name", "")),
            "type": str(item.get("vtype", "")),
            "lower_bound": _clean_number(item.get("lb")),
            "upper_bound": _clean_number(item.get("ub")),
            "ordinary_solution_value": _clean_number(item.get("value")),
        }
        for item in inventory.get("variables", []) or []
        if str(item.get("name", ""))
    }


def _found_test(result: Dict[str, Any]) -> Dict[str, Any]:
    for item in result.get("tests", []) or []:
        if isinstance(item, dict) and str(item.get("status", "")).upper() == "WITNESS_FOUND":
            return item
    return {}


def _numeric_point(result: Dict[str, Any]) -> Dict[str, float]:
    test = _found_test(result)
    candidates = [
        test.get("variables"),
        result.get("witness"),
        result.get("fractional_values"),
    ]
    point: Dict[str, float] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        # Implication harnesses may wrap the actual point under "variables".
        if isinstance(candidate.get("variables"), dict):
            candidate = candidate["variables"]
        for name, value in candidate.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                clean = _clean_number(value)
                if clean is not None:
                    point[str(name)] = float(clean)
    return dict(sorted(point.items()))


def _probe_aggregate(entry: Dict[str, Any], point: Dict[str, float]) -> Dict[str, Any]:
    """Compute neutral arithmetic facts alongside the prompt-visible normalized probe."""
    probe = entry.get("normalized_probe") or {}
    params = probe.get("parameters", {}) if isinstance(probe, dict) else {}
    terms = params.get("lhs_terms", []) or []
    if not terms or not point:
        return {}
    components = []
    total = 0.0
    for term in terms:
        if not isinstance(term, dict):
            return {}
        name = str(term.get("var", ""))
        if name not in point:
            return {}
        try:
            coefficient = float(term.get("coeff"))
        except (TypeError, ValueError):
            return {}
        contribution = coefficient * point[name]
        components.append({
            "variable": name,
            "coefficient": _clean_number(coefficient),
            "value": _clean_number(point[name]),
            "contribution": _clean_number(contribution),
        })
        total += contribution
    try:
        rhs = _clean_number(float(params.get("rhs")))
    except (TypeError, ValueError):
        rhs = None
    return {
        "name": "deterministic_linear_aggregate",
        "lhs_value": _clean_number(total),
        "comparison_operator": str(params.get("sense", "")),
        "rhs_reference_value": rhs,
        "components": components,
        "component_count": len(components),
    }


def _property_facts(entry: Dict[str, Any],
                    inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = entry.get("execution_result") or entry.get("structural_evidence") or {}
    records = _variable_map(inventory)
    names: List[str] = []
    for value in (
            result.get("target_variables"),
            (entry.get("normalized_probe") or {}).get("parameters", {}).get(
                "target_variables"),
            (result.get("observation") or {}).get("variables")):
        if not isinstance(value, list):
            continue
        for item in value:
            name = str(item.get("name", "")) if isinstance(item, dict) else str(item)
            if name:
                names.append(name)
    reason = str(result.get("reason") or result.get("structural_detail") or
                 result.get("message") or "")
    for name in records:
        if name in reason:
            names.append(name)
    return [records[name] for name in dict.fromkeys(names) if name in records]


def _variable_meanings(metadata: Dict[str, Any],
                       variable_names: Iterable[str]) -> List[Dict[str, Any]]:
    names = set(variable_names)
    selected = []
    for item in metadata.get("variables", []) or []:
        if not isinstance(item, dict):
            continue
        group = str(item.get("variable", ""))
        if (not names or group in names or
                any(name.startswith(group + "_") or name.startswith(group + "[")
                    for name in names)):
            selected.append({
                key: item[key] for key in (
                    "variable", "meaning", "index_meaning", "index_domain",
                    "declared_type", "lower_bound_stated")
                if key in item
            })
    # Avoid an empty semantic dictionary when exact model names differ from contract group names.
    if not selected:
        selected = [
            {key: item[key] for key in (
                "variable", "meaning", "index_meaning", "index_domain",
                "declared_type", "lower_bound_stated")
             if key in item}
            for item in (metadata.get("variables", []) or [])[:40]
            if isinstance(item, dict)
        ]
    return selected


def _provenance(result: Dict[str, Any], structural: bool) -> Dict[str, Any]:
    test = _found_test(result)
    replay = test.get("full_model_replay") or result.get("full_model_replay") or {}
    confirmed = (
        True if structural else
        bool(test.get("post_validation_confirmed",
                      result.get("post_validation_confirmed", False))))
    arithmetic = (
        True if structural else
        bool(test.get("arithmetic_replay_agrees",
                      result.get("arithmetic_replay_agrees", False))))
    feasible = True if structural else bool(
        isinstance(replay, dict) and replay.get("feasible") is True)
    return {
        "certificate_source": (
            "deterministic_structural_observation" if structural
            else "solver_point_with_deterministic_replay"),
        "post_validation_confirmed": confirmed,
        "arithmetic_replay_agrees": arithmetic,
        "full_model_replay_feasible": feasible,
    }


def build_witness_certificate(requirement: Dict[str, Any], metadata: Dict[str, Any],
                              entry: Dict[str, Any],
                              inventory: Dict[str, Any]) -> Dict[str, Any]:
    """Convert raw execution evidence into a compact, neutral, deterministic certificate."""
    del requirement, metadata  # inputs are intentionally not copied into the certificate
    result = entry.get("execution_result") or entry.get("structural_evidence") or {}
    source = str(entry.get("decision_source", ""))
    template = str((entry.get("normalized_probe") or {}).get("probe_template", ""))
    solver_backed_bound = (
        template == "check_variable_property" and
        str(result.get("structural_status", "")) == "REQUIRES_SOLVER")
    structural = (
        source == "structural_witness" or
        (template in {"check_variable_property", "check_objective_terms"} and
         not solver_backed_bound))
    point = _numeric_point(result)
    aggregate = _probe_aggregate(entry, point)
    property_facts = _property_facts(entry, inventory)
    found = _found_test(result)

    observations: List[Dict[str, Any]] = []
    if aggregate:
        observations.append(aggregate)
    residual = found.get("recomputed_violation", result.get("recomputed_violation"))
    margin = found.get("acceptance_margin", result.get("acceptance_margin"))
    scale = found.get("scale", result.get("scale"))
    if residual is not None or margin is not None:
        observations.append({
            "name": "replayed_numeric_residual",
            "value": _clean_number(residual),
            "acceptance_margin": _clean_number(margin),
            "scale": _clean_number(scale),
        })
    if property_facts:
        observations.append({
            "name": "declared_variable_properties",
            "variables": property_facts,
        })
    objective = (result.get("observation") or {}).get("objective")
    if template == "check_objective_terms" and not objective:
        objective = inventory.get("objective")
    if structural and isinstance(objective, dict) and objective:
        observations.append({
            "name": "declared_objective",
            "sense": str(objective.get("sense", "")),
            "terms": objective.get("terms", []),
            "constant": _clean_number(objective.get("constant")),
        })
    detail = str(result.get("reason") or result.get("structural_detail") or
                 result.get("message") or "")
    if detail:
        observations.append({"name": "deterministic_observation", "detail": detail})

    provenance = _provenance(result, structural)
    concrete = bool(point or property_facts or objective)
    safe_provenance = bool(
        structural or (
            provenance["post_validation_confirmed"] and
            provenance["arithmetic_replay_agrees"] and
            provenance["full_model_replay_feasible"]))
    eligible = bool(concrete and safe_provenance)
    variable_names = sorted(set(point) | {
        str(item.get("name", "")) for item in property_facts if item.get("name")
    })
    grouping_material = point or property_facts or observations
    certificate = {
        "certificate_version": CERTIFICATE_VERSION,
        "certificate_kind": (
            "structural_facts" if structural
            else "concrete_solver_point"),
        "candidate_point": point,
        "observations": observations,
        "variable_names": variable_names,
        "provenance": provenance,
        "eligible_for_llm_review": eligible,
        "ineligible_reason": "" if eligible else (
            "no concrete point or property facts"
            if not concrete else "solver witness did not pass deterministic replay gates"),
        "witness_group_id": _json_hash(grouping_material)[:16],
    }
    certificate["certificate_sha256"] = _json_hash(certificate)
    return certificate


def _visible_verifier_input(requirement: Dict[str, Any], metadata: Dict[str, Any],
                            certificate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "requirement_id": str(requirement.get("requirement_id", "")),
        "requirement_text": str(requirement.get("requirement_text", "")),
        "problem_data": metadata.get("fixed_parameters", {}),
        "variable_meanings": _variable_meanings(
            metadata, certificate.get("variable_names", [])),
        "measured_facts_and_certificate": certificate,
    }


def _visible_probe_aware_input(requirement: Dict[str, Any], metadata: Dict[str, Any],
                               certificate: Dict[str, Any],
                               entry: Dict[str, Any]) -> Dict[str, Any]:
    visible = _visible_verifier_input(requirement, metadata, certificate)
    visible["exact_normalized_generated_probe"] = entry.get("normalized_probe") or {
        "probe_template": "structural_evidence",
        "claim": "candidate-declared structural property",
        "parameters": {},
    }
    return visible


def _normalise_verifier_decision(value: Any) -> str:
    text = str(value or "").strip().upper().replace(" ", "_")
    return text if text in VERIFIER_DECISIONS else ""


def _verify_with_prompt(requirement: Dict[str, Any], metadata: Dict[str, Any],
                        entry: Dict[str, Any], inventory: Dict[str, Any],
                        *, call_json: CallJSON, model: str,
                        seed: Optional[int], max_tokens: int) -> Dict[str, Any]:
    certificate = build_witness_certificate(requirement, metadata, entry, inventory)
    visible = _visible_probe_aware_input(requirement, metadata, certificate, entry)
    base = {
        "requirement_id": str(requirement.get("requirement_id", "")),
        "role": ROLE_WITNESS_VERIFIER,
        "model_used": model,
        "visible_input": visible,
        "certificate": certificate,
    }
    if not certificate["eligible_for_llm_review"]:
        return {
            **base, "status": "UNRESOLVED", "decision": None,
            "reason": certificate["ineligible_reason"],
            "requirement_demands": "", "decisive_check": "",
            "calculation": "", "model_called": False, "model_call_count": 0,
            "parse_error": "", "technical_reason": certificate["ineligible_reason"],
            "raw_response": "", "call_metadata": {},
            "call_records": [],
        }
    prompt = WITNESS_VERIFIER_PROMPT.format(
        visible_input=json.dumps(visible, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), default=str))
    calls = []
    obj: Dict[str, Any] = {}
    error = ""
    response: Dict[str, Any] = {}
    decision = ""
    for call_index in range(MAX_TECHNICAL_RETRIES):
        call_seed = seed
        candidate_obj, candidate_error, candidate_response = call_json(
            prompt, call_seed, int(max_tokens))
        candidate_obj = candidate_obj or {}
        raw_decision = str(candidate_obj.get("decision", "")).strip().upper()
        candidate_decision = _normalise_verifier_decision(raw_decision)
        reason = str(candidate_obj.get("reason", "") or "")
        valid_shape = (
            not candidate_error and
            raw_decision in VERIFIER_DECISIONS and
            bool(reason.strip()))
        calls.append({
            "attempt": call_index + 1,
            "valid_shape": valid_shape,
            "parse_error": candidate_error,
            "raw_decision": raw_decision,
            "call_metadata": candidate_response.get("call_metadata", {}),
        })
        obj, error, response, decision = (
            candidate_obj, candidate_error, candidate_response, candidate_decision)
        if valid_shape:
            break
        error = candidate_error or "invalid verifier decision shape"
    if error or not calls[-1]["valid_shape"]:
        decision = ""
    unresolved = not bool(decision)
    return {
        **base,
        "status": "UNRESOLVED" if unresolved else "DECIDED",
        "decision": decision or None,
        "reason": str(obj.get("reason", "") or error or "unparseable verifier response"),
        "requirement_demands": str(obj.get("requirement_demands", "")),
        "decisive_check": str(
            obj.get("decisive_check", "") or obj.get("calculation", "")),
        # Backward-compatible analysis field.
        "calculation": str(
            obj.get("decisive_check", "") or obj.get("calculation", "")),
        "model_called": True, "model_call_count": len(calls),
        "parse_error": error,
        "technical_reason": error if unresolved else "",
        "raw_response": str(response.get("text", "")),
        "call_metadata": response.get("call_metadata", {}),
        "call_records": calls,
    }


def verify_probe_aware(requirement: Dict[str, Any], metadata: Dict[str, Any],
                       entry: Dict[str, Any], inventory: Dict[str, Any],
                       *, call_json: CallJSON, model: str,
                       seed: Optional[int], max_tokens: int = 2400) -> Dict[str, Any]:
    """Operations-research arm: verify the witness while inspecting the exact probe."""
    return _verify_with_prompt(
        requirement, metadata, entry, inventory, call_json=call_json,
        model=model, seed=seed, max_tokens=max_tokens)


def _certificate_margin(certificate: Dict[str, Any]) -> Tuple[Optional[float],
                                                               Optional[float]]:
    for observation in certificate.get("observations", []) or []:
        if observation.get("name") != "replayed_numeric_residual":
            continue
        try:
            residual = float(observation.get("value"))
        except (TypeError, ValueError):
            residual = None
        try:
            margin = float(observation.get("acceptance_margin"))
        except (TypeError, ValueError):
            margin = None
        return residual, margin
    return None, None


def root_cause_features(confirmed: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Deterministic evidence features supplied to, but not decided by, the adjudicator."""
    items = []
    for record in confirmed:
        certificate = record.get("certificate") or {}
        residual, margin = _certificate_margin(certificate)
        normalized = (
            residual / margin
            if residual is not None and margin is not None and margin > 0 else None)
        items.append({
            "requirement_id": record["requirement_id"],
            "evidence_authority_tier": int(record.get("evidence_tier", 3) or 3),
            "witness_group_id": certificate.get("witness_group_id", ""),
            "variable_names": sorted(certificate.get("variable_names", [])),
            "replayed_residual": residual,
            "acceptance_margin": margin,
            "margin_multiple": normalized,
        })
    pairwise = []
    for left, right in combinations(items, 2):
        left_vars, right_vars = set(left["variable_names"]), set(right["variable_names"])
        union = left_vars | right_vars
        overlap = left_vars & right_vars
        pairwise.append({
            "left_requirement_id": left["requirement_id"],
            "right_requirement_id": right["requirement_id"],
            "same_witness_assignment": bool(
                left["witness_group_id"] and
                left["witness_group_id"] == right["witness_group_id"]),
            "shared_variables": sorted(overlap),
            "variable_overlap_jaccard": (
                round(len(overlap) / len(union), 6) if union else None),
            "left_variables_subset_of_right": bool(left_vars and left_vars <= right_vars),
            "right_variables_subset_of_left": bool(right_vars and right_vars <= left_vars),
        })
    return {"per_requirement": items, "pairwise": pairwise}


def _root_visible_input(requirements: Sequence[Dict[str, Any]],
                        confirmed: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_id = {str(item.get("requirement_id", "")): item for item in requirements}
    failures = []
    for record in confirmed:
        rid = record["requirement_id"]
        requirement = by_id.get(rid, {})
        failures.append({
            "requirement_id": rid,
            "requirement_text": str(requirement.get("requirement_text", "")),
            "evidence_authority_tier": int(record.get("evidence_tier", 3) or 3),
            "witness_facts": record.get("certificate", {}),
        })
    return {
        "confirmed_failures": failures,
        "comparison_features": root_cause_features(confirmed),
    }


def adjudicate_root_cause(requirements: Sequence[Dict[str, Any]],
                          confirmed: Sequence[Dict[str, Any]],
                          *, call_json: CallJSON, model: str,
                          seed: Optional[int], max_tokens: int = 1800,
                          deterministic_fallback_ranking: Optional[
                              Sequence[str]] = None,
                          evidence_tiers: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    ids = [str(item.get("requirement_id", "")) for item in confirmed]
    tier_map = {
        rid: int((evidence_tiers or {}).get(
            rid, next((item.get("evidence_tier", 3) for item in confirmed
                       if str(item.get("requirement_id", "")) == rid), 3)) or 3)
        for rid in ids
    }
    base = {
        "role": ROLE_ROOT_CAUSE_ADJUDICATOR,
        "model_used": model,
        "confirmed_requirement_ids": ids,
        "evidence_authority_tiers": tier_map,
    }
    if not ids:
        return {
            **base, "decision": "NOT_RUN", "primary_requirement_id": "",
            "ranked_requirement_ids": [], "collateral_requirement_ids": [],
            "reason": "no witness was confirmed", "model_called": False,
            "model_call_count": 0, "root_agent_technical_failure": False,
            "visible_input": {}, "parse_error": "", "raw_response": "",
            "call_metadata": {}, "call_records": [],
        }
    if any(tier == 1 for tier in tier_map.values()):
        fallback = [
            str(value) for value in (deterministic_fallback_ranking or [])
            if str(value) in set(ids)
        ]
        fallback = list(dict.fromkeys(fallback))
        fallback.extend(rid for rid in ids if rid not in fallback)
        fallback_position = {rid: position for position, rid in enumerate(fallback)}
        ranked = sorted(
            fallback,
            key=lambda rid: (tier_map.get(rid, 3), fallback_position[rid]),
        )
        return {
            **base, "decision": RANKED, "primary_requirement_id": ranked[0],
            "ranked_requirement_ids": ranked,
            "collateral_requirement_ids": ranked[1:],
            "reason": (
                "Tier-1 authoritative evidence bypassed the root agent; "
                "deterministic tier-preserving ranking used"),
            "model_called": False, "model_call_count": 0,
            "root_agent_technical_failure": False,
            "visible_input": _root_visible_input(requirements, confirmed),
            "parse_error": "", "raw_response": "", "call_metadata": {},
            "call_records": [],
        }

    if len(ids) == 1:
        return {
            **base, "decision": RANKED, "primary_requirement_id": ids[0],
            "ranked_requirement_ids": ids, "collateral_requirement_ids": [],
            "reason": "only one witness was confirmed", "model_called": False,
            "model_call_count": 0, "root_agent_technical_failure": False,
            "visible_input": _root_visible_input(requirements, confirmed),
            "parse_error": "", "raw_response": "", "call_metadata": {},
            "call_records": [],
        }

    visible = _root_visible_input(requirements, confirmed)
    visible["evidence_authority_tiers"] = tier_map
    prompt = ROOT_CAUSE_PROMPT.format(
        visible_input=json.dumps(visible, ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), default=str))
    supplied = set(ids)
    calls = []
    obj: Dict[str, Any] = {}
    error = ""
    response: Dict[str, Any] = {}
    ranked: List[str] = []
    primary = ""
    collateral: List[str] = []
    valid = False
    for call_index in range(MAX_TECHNICAL_RETRIES):
        call_seed = seed
        candidate_obj, candidate_error, candidate_response = call_json(
            prompt, call_seed, int(max_tokens))
        candidate_obj = candidate_obj or {}
        candidate_ranked = (
            [str(value) for value in candidate_obj.get("ranked_requirement_ids", [])]
            if isinstance(candidate_obj.get("ranked_requirement_ids"), list) else [])
        candidate_primary = str(
            candidate_obj.get("primary_requirement_id", "") or "")
        candidate_tier_sequence = [tier_map.get(rid, 3) for rid in candidate_ranked]
        tier_order_valid = candidate_tier_sequence == sorted(candidate_tier_sequence)
        valid = (
            not candidate_error and
            str(candidate_obj.get("decision", "")).strip().upper() == RANKED and
            len(candidate_ranked) == len(ids) and
            len(set(candidate_ranked)) == len(ids) and
            set(candidate_ranked) == supplied and
            candidate_primary == candidate_ranked[0] and
            tier_order_valid)
        calls.append({
            "attempt": call_index + 1,
            "valid_complete_ranking": valid,
            "parse_error": candidate_error,
            "returned_ids": candidate_ranked,
            "returned_evidence_tiers": candidate_tier_sequence,
            "tier_order_valid": tier_order_valid,
            "call_metadata": candidate_response.get("call_metadata", {}),
        })
        obj, error, response = candidate_obj, candidate_error, candidate_response
        if valid:
            ranked = candidate_ranked
            primary = candidate_primary
            collateral = [
                str(value)
                for value in candidate_obj.get("collateral_requirement_ids", [])
                if str(value) in supplied and str(value) != primary
            ] if isinstance(
                candidate_obj.get("collateral_requirement_ids"), list) else []
            collateral = list(dict.fromkeys(collateral))
            break
        error = candidate_error or (
            "root adjudicator must rank every supplied requirement exactly once and preserve "
            "ascending evidence-authority tiers")

    technical_failure = not valid
    if technical_failure:
        fallback = [
            str(value) for value in (deterministic_fallback_ranking or [])
            if str(value) in supplied
        ]
        fallback = list(dict.fromkeys(fallback))
        fallback.extend(rid for rid in ids if rid not in fallback)
        fallback_position = {rid: position for position, rid in enumerate(fallback)}
        ranked = sorted(
            fallback,
            key=lambda rid: (tier_map.get(rid, 3), fallback_position[rid]),
        )
        primary = ranked[0]
        collateral = ranked[1:]
    return {
        **base, "decision": RANKED, "primary_requirement_id": primary,
        "ranked_requirement_ids": ranked,
        "collateral_requirement_ids": collateral,
        "reason": (
            "root agent technical failure; current deterministic ranking used"
            if technical_failure else
            str(obj.get("reason", "") or "complete evidence-grounded ranking")),
        "model_called": True, "model_call_count": len(calls),
        "root_agent_technical_failure": technical_failure,
        "technical_failure_reason": error if technical_failure else "",
        "visible_input": visible,
        "parse_error": error, "raw_response": str(response.get("text", "")),
        "call_metadata": response.get("call_metadata", {}),
        "call_records": calls,
    }


def format_live_verification(accounting: Dict[str, Any]) -> str:
    """Format the retained probe-aware verifier and root-cause result."""
    lines = ["PROBE-AWARE WITNESS VERIFIER:"]
    records = accounting.get("witness_probe_aware_records", {}) or {}
    if not records:
        lines.append("  no raw FAIL witness required review")
    for rid, record in records.items():
        lines.append(
            f"  {rid}: decision={record.get('decision')} confidence=not_reported")
    root = accounting.get("root_cause_record", {}) or {}
    lines.append("ROOT-CAUSE ADJUDICATOR:")
    lines.append(
        f"  decision={root.get('decision', 'NOT_RUN')} "
        f"primary={root.get('primary_requirement_id', '') or 'none'} "
        f"ranking={root.get('ranked_requirement_ids', [])}")
    return "\n".join(lines)


def assert_probe_aware_visible_contract(record: Dict[str, Any]) -> None:
    """Guard the probe-aware arm's exact allow-list and prevent answer leakage."""
    visible = record.get("visible_input", {})
    allowed = {
        "requirement_id", "requirement_text", "problem_data", "variable_meanings",
        "measured_facts_and_certificate", "exact_normalized_generated_probe",
    }
    extra = set(visible) - allowed
    if extra:
        raise AssertionError(
            f"probe-aware verifier received forbidden fields: {sorted(extra)}")
    if "exact_normalized_generated_probe" not in visible:
        raise AssertionError("probe-aware verifier did not receive the exact normalized probe")
    blob = json.dumps(visible, sort_keys=True).lower()
    for token in (
            '"judge_votes"', '"mutation"', '"gold"', '"status": "fail"',
            '"primary_suspected_requirement_id"'):
        if token in blob:
            raise AssertionError(f"probe-aware verifier input leaked {token}")
