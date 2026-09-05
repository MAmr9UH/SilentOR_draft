#!/usr/bin/env python3
"""Two-stage probe-validation and repair helpers for retained V42."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional, Sequence

ACCEPT = "ACCEPT"
REPAIR = "REPAIR"
VERDICTS = (ACCEPT, REPAIR)

ACTION_EXECUTE = "EXECUTE"
ACTION_RECONSTRUCT = "RECONSTRUCT"
ACTION_TECHNICAL_ERROR = "TECHNICAL_ERROR"

# =============================================================================================
# LEAKAGE AUDIT
# =============================================================================================
# Any field whose presence in an agent's input would reveal the answer, the mutation, the oracle,
# the expected diagnosis, or another agent's decision.  Checked by exact key name and by
# substring at every active agent call.
DENIED_INPUT_FIELDS = frozenset({
    "gold_objective", "gold", "expected_objective", "reference_objective",
    "mutation_label", "mutant_label", "is_mutant", "injected_requirement",
    "injected_fault", "mutation_location", "source_diff", "diff",
    "expected_diagnosis", "expected_taxonomy", "taxonomy_answer", "answer",
    "oracle_contract", "certified_normative_binding", "certification_witness",
    "hidden_manifest", "checker_spec", "requirement_checker",
    "other_judge_verdict", "peer_verdict", "panel_verdicts", "votes",
    "judge1_verdict", "judge2_verdict", "judge3_verdict", "prior_verdict",
})

_DENIED_SUBSTRINGS = ("gold", "mutant", "mutation", "oracle", "certified_normative",
                      "expected_diagnosis", "taxonomy_answer", "peer_verdict",
                      "other_judge", "panel_verdict")


def audit_inputs(agent: str, payload: Dict[str, Any], allowed: Sequence[str],
                 requirement_id: str = "") -> Dict[str, Any]:
    """Record the EXACT input field names an agent received, and flag any leakage.

    Returns an audit record.  ``violations`` is non-empty when a denied field reached the agent or
    when a field outside the agent's declared allow-list was passed. Every active agent call uses
    this audit, so a leakage regression is visible in the log rather than silent.
    """
    received = sorted(payload.keys())
    denied = sorted(k for k in received
                    if k in DENIED_INPUT_FIELDS
                    or any(sub in k.lower() for sub in _DENIED_SUBSTRINGS))
    undeclared = sorted(set(received) - set(allowed))
    return {
        "agent": agent,
        "requirement_id": requirement_id,
        "input_fields_received": received,
        "input_fields_allowed": sorted(allowed),
        "undeclared_fields": undeclared,
        "denied_fields_present": denied,
        "violations": denied + [f"undeclared:{k}" for k in undeclared],
        "leak_free": not denied and not undeclared,
    }


def assert_leak_free(record: Dict[str, Any]) -> None:
    if record["denied_fields_present"]:
        raise AssertionError(
            f"leakage: agent {record['agent']} received "
            f"{record['denied_fields_present']}")


# =============================================================================================
# VOTING
# =============================================================================================
def tally_panel(verdicts: Sequence[str], *, repair_used: bool = False) -> Dict[str, Any]:
    """Require unanimous ACCEPT at each approved judge stage."""
    del repair_used
    vs = [str(v).upper() for v in verdicts]
    accepts, repairs = vs.count(ACCEPT), vs.count(REPAIR)
    if vs and accepts == len(vs):
        action, reason = ACTION_EXECUTE, "all judges in this stage ACCEPT"
    else:
        action, reason = ACTION_RECONSTRUCT, "one or more judges require REPAIR"
    return {"action": action, "reason": reason, "verdicts": vs,
            "accept_count": accepts, "repair_count": repairs,
            "margin": f"{accepts}A/{repairs}P"}


# =============================================================================================
# REPAIR FEEDBACK
# =============================================================================================
def anonymous_repair_note(judge_records: Sequence[Dict[str, Any]], *,
                          deterministic_findings: Optional[Dict[str, Any]] = None,
                          suggest_different_template: bool = False) -> str:
    """Combine substantive findings without exposing judge identity or perceived authority."""
    patches = []
    reasons = []
    for rec in judge_records:
        patch = rec.get("patch")
        if rec.get("verdict") == REPAIR and isinstance(patch, dict) and \
                any(bool(value) for value in patch.values()):
            patches.append(patch)
        if rec.get("verdict") == REPAIR:
            # Merge every available substantive item.  No judge role/name is copied, so the next
            # generator sees one anonymous combined instruction rather than attributed votes.
            for reason in (rec.get("reason"),):
                if str(reason or "").strip():
                    reasons.append(str(reason).strip())
    findings = deterministic_findings or {}
    if not patches and not reasons and not findings and not suggest_different_template:
        return ""
    parts = [
        "\nPrevious attempt was not accepted."
    ]
    if reasons:
        parts.append("\nSUBSTANTIVE FAILURES: " + "; ".join(dict.fromkeys(reasons)))
    if patches:
        parts.append("\nEXACT STRUCTURED PATCHES TO APPLY TOGETHER:\n" +
                     json.dumps(patches, ensure_ascii=False, indent=2, default=str))
    if findings:
        parts.append("\nCACHED DETERMINISTIC FINDINGS:\n" +
                     json.dumps(findings, ensure_ascii=False, indent=2, default=str))
    if suggest_different_template:
        parts.append(
            "\nTEMPLATE INSTRUCTION: select a different compatible template on the next attempt.")
    parts.append(
        "\nMUST REMAIN UNCHANGED: every field not named in a patch, including all other "
        "variables, coefficients, operators, RHS values, coverage, and implication structure."
        "\nReturn the complete repaired probe, not only the patch.")
    return "".join(parts)


def _repair_note(judge_records: Sequence[Dict[str, Any]]) -> str:
    """Backward-compatible anonymous repair note."""
    return anonymous_repair_note(judge_records)


# =============================================================================================
# LIVE-LOOP ENTRY POINT
# =============================================================================================
# The live loop projects a deterministic abstract view from the generated probe for audit records.
# Judges 1–2 inspect the generated structured probe; Judge 3 later inspects the exact normalized
# executable together with the generated claim.

_SENSE_KEYS = ("sense", "required_sense", "relation")


def _first(mapping: Dict[str, Any], keys: Sequence[str], default: str = "") -> str:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def abstract_view_from_probe(probe: Dict[str, Any], requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic ABSTRACT projection of an executable probe: what is checked, not how."""
    params = probe.get("parameters") or {}
    rows = [r for r in (params.get("expected_rows") or []) if isinstance(r, dict)]
    row = params.get("expected_row") if isinstance(params.get("expected_row"), dict) else None
    source = row or (rows[0] if rows else params)
    sense = _first(source, _SENSE_KEYS) or _first(params, _SENSE_KEYS)
    rhs = source.get("rhs", params.get("rhs", params.get("expected_value", "")))
    terms = [t for t in (source.get("lhs_terms") or []) if isinstance(t, dict)]
    target = (str(terms[0].get("var", "")) if terms
              else str((params.get("target_symbols") or params.get("target_variables")
                        or [""])[0] if (params.get("target_symbols")
                                        or params.get("target_variables")) else ""))
    return {
        "requirement_id": str(probe.get("requirement_id", "")),
        "template": str(probe.get("probe_template", "")),
        "target": target or str(requirement.get("category", "")),
        "for_each": "row" if rows else "",
        "sum_over": "terms" if len(terms) > 1 else "",
        "sense": sense,
        "rhs": "" if rhs in (None, "") else str(rhs),
        "claim": str(probe.get("claim", "")),
        "projected": True,
    }


def _judge_stage(*, phase: str, call_json: Callable, req: Dict[str, Any],
                 payload: Dict[str, Any], probe: Dict[str, Any],
                 model_structure: Dict[str, Any], panel: Callable,
                 seed_for: Callable, metadata: Optional[Dict[str, Any]] = None,
                 claim: str = "") -> Dict[str, Any]:
    """Run one approved judge stage and convert technical failures to local unresolved state."""
    rid = str(req.get("requirement_id", ""))
    audit: List[Dict[str, Any]] = []
    abstract = abstract_view_from_probe(probe, req)
    if str(probe.get("requirement_id", "")) != rid:
        return {
            "requirement_id": rid, "action": ACTION_TECHNICAL_ERROR,
            "pipeline_error": False, "requirement_unresolved": True,
            "technical_stage": phase,
            "error": "probe requirement_id changed before judging",
            "input_audit": audit, "judges": [], "panel": None,
            "abstract_probe": abstract, "structured_probe": probe,
            "repair_note": "", "leak_free": True,
        }
    judge_records = panel(
        call_json=call_json, req=req, payload=payload, abstract=abstract,
        executable=probe, model_structure=model_structure, seed_for=seed_for,
        audit=audit, metadata=metadata, phase=phase, claim=claim)
    if any(str(record.get("verdict", "")) == "TECHNICAL_ERROR"
           for record in judge_records):
        return {
            "requirement_id": rid, "action": ACTION_TECHNICAL_ERROR,
            "pipeline_error": False, "requirement_unresolved": True,
            "technical_stage": phase,
            "error": "one or more judge decisions failed the structured contract",
            "input_audit": audit, "judges": judge_records, "panel": None,
            "abstract_probe": abstract, "structured_probe": probe,
            "repair_note": "", "leak_free": all(r["leak_free"] for r in audit),
        }
    verdicts = [str(record.get("verdict", "")) for record in judge_records]
    decision = tally_panel(verdicts)
    return {
        "requirement_id": rid, "action": decision["action"],
        "pipeline_error": False, "requirement_unresolved": False,
        "technical_stage": "", "error": "", "input_audit": audit,
        "judges": judge_records, "panel": decision,
        "abstract_probe": abstract, "structured_probe": probe,
        "repair_note": _repair_note(judge_records),
        "leak_free": all(r["leak_free"] for r in audit),
    }


def judge_generated_probe_first_two(*, call_json: Callable, req: Dict[str, Any],
                                    payload: Dict[str, Any], probe: Dict[str, Any],
                                    model_structure: Dict[str, Any], panel: Callable,
                                    seed_for: Callable,
                                    metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run Judges 1 and 2 on the generated structured probe before compilation."""
    return _judge_stage(
        phase="first_two", call_json=call_json, req=req, payload=payload, probe=probe,
        model_structure=model_structure, panel=panel, seed_for=seed_for,
        metadata=metadata)


def judge_final_probe_third(*, call_json: Callable, req: Dict[str, Any],
                            payload: Dict[str, Any], probe: Dict[str, Any], claim: str,
                            model_structure: Dict[str, Any], panel: Callable,
                            seed_for: Callable,
                            metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Run Judge 3 on the claim and exact final normalized executable probe."""
    return _judge_stage(
        phase="judge3", call_json=call_json, req=req, payload=payload, probe=probe,
        model_structure=model_structure, panel=panel, seed_for=seed_for,
        metadata=metadata, claim=claim)


# =============================================================================================
# REPAIR INSTRUCTIONS
# =============================================================================================
FORMAT_ONLY_REPAIR = """Fix JSON syntax and schema only.
Preserve all variables, coefficients, operators, RHS values,
implication structure, and mathematical meaning exactly."""

NUMERIC_FIELD_RULE = ("Numeric JSON fields must contain a single evaluated number, never an "
                      'arithmetic expression: write "rhs": -45.0, never "rhs": 30.0 - 75.0 + 0.0.')


def format_only_repair_note(parse_error: str = "") -> str:
    """A malformed-JSON attempt gets a FORMAT-ONLY repair: never a semantic rewrite.

    Asking for semantic changes in response to a syntax error is how a correct probe gets
    corrupted while being reformatted.
    """
    detail = f" Parser reported: {parse_error}." if parse_error else ""
    return (f"\nYour previous response was not valid JSON.{detail}\n{FORMAT_ONLY_REPAIR}\n"
            f"{NUMERIC_FIELD_RULE}")


def semantic_repair_note(failure: str, field: str, keep_unchanged: Sequence[str] = ()) -> str:
    """Every semantic repair states: exact failure, exact field to change, what must NOT change."""
    keep = ", ".join(keep_unchanged) if keep_unchanged else (
        "every other variable, coefficient, operator, RHS value and the implication structure")
    return ("\nPrevious attempt was not accepted."
            f"\nEXACT FAILURE: {failure}"
            f"\nEXACT FIELD TO CHANGE: {field}"
            f"\nMUST REMAIN UNCHANGED: {keep}"
            f"\n{NUMERIC_FIELD_RULE}")
