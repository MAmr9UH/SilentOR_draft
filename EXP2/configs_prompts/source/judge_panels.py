#!/usr/bin/env python3
"""The retained V42 three-judge probe-validation panel.

    Judge 1  semantic fidelity          LLM
    Judge 2  mathematical correctness   LLM
    Judge 3  claim/executable equivalence LLM after normalization and compilation

Leakage rules:
  * No judge receives another judge's verdict, so every ACCEPT is independent.
  * No judge receives a gold objective, mutation label/location, source diff, oracle contract,
    certification witness, expected diagnosis, or checker spec.
  * Every judge's exact input field names are logged via ``probe_roundtrip.audit_inputs``.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import problem_metadata as pmeta
import probe_roundtrip as prt

ACCEPT, REPAIR = prt.ACCEPT, prt.REPAIR
TECHNICAL_ERROR = "TECHNICAL_ERROR"

VERSION_B = "B_all_llm"

PATCH_FIELDS = (
    "terms_to_add",
    "terms_to_remove",
    "coefficients_to_replace",
    "constraint_sense_to_replace",
    "right_hand_side_to_replace",
    "property_to_replace",
    "expected_value_to_replace",
    "coverage_to_replace",
)


def empty_patch() -> Dict[str, Any]:
    """Canonical no-op patch returned by an ACCEPT vote."""
    return {}


def _patch_has_change(patch: Dict[str, Any]) -> bool:
    return any(bool(patch.get(field)) for field in PATCH_FIELDS)


def _normalize_patch(value: Any) -> Tuple[Dict[str, Any], str]:
    """Validate a judge patch without inventing a missing change.

    Replacement objects require an exact destination path and an exact replacement value.  Term
    changes additionally require a variable name; coefficient replacements require the new
    coefficient.  A vague sentence therefore cannot silently become a valid REPAIR vote.
    """
    patch: Dict[str, Any] = {}
    if value in (None, "", {}):
        return patch, ""
    if not isinstance(value, dict):
        return patch, "patch_must_be_an_object"
    unknown = sorted(set(value) - set(PATCH_FIELDS))
    if unknown:
        return patch, f"unknown_patch_fields:{','.join(unknown)}"
    for field in PATCH_FIELDS:
        raw = value.get(field)
        if field in ("terms_to_add", "terms_to_remove", "coefficients_to_replace"):
            if raw in (None, []):
                continue
            if not isinstance(raw, list):
                return patch, f"{field}_must_be_a_list"
            normalized_items = []
            for item in raw:
                if not isinstance(item, dict) or not str(item.get("variable", "")).strip():
                    return patch, f"{field}_requires_exact_variable_objects"
                if field != "terms_to_remove" and "coefficient" not in item and "to" not in item:
                    return patch, f"{field}_requires_exact_replacement_value"
                normalized_items.append(dict(item))
            patch[field] = normalized_items
        else:
            if raw is None:
                continue
            if not isinstance(raw, dict) or not str(raw.get("path", "")).strip() or "to" not in raw:
                return patch, f"{field}_requires_path_and_to"
            patch[field] = dict(raw)
    return patch, ""


PATCH_SCHEMA_TEXT = """Always return every patch field. For ACCEPT, use empty arrays and null
replacements. For REPAIR, change only the exact affected fields:
{
  "terms_to_add":[{"variable":"<exact variable>","coefficient":<number>}],
  "terms_to_remove":[{"variable":"<exact variable>"}],
  "coefficients_to_replace":[{"variable":"<exact variable>","from":<old>,"to":<new>}],
  "constraint_sense_to_replace":{"path":"parameters.sense","from":"<old>","to":"<new>"} or null,
  "right_hand_side_to_replace":{"path":"parameters.rhs","from":<old>,"to":<new>} or null,
  "property_to_replace":{"path":"parameters.property","from":"<old>","to":"<new>"} or null,
  "expected_value_to_replace":{"path":"parameters.expected_value","from":<old>,"to":<new>} or null,
  "coverage_to_replace":{"path":"<exact coverage path>","from":<old>,"to":<new>} or null
}"""


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


# =============================================================================================
# JUDGE 1 -- semantic fidelity (LLM in BOTH versions)
# =============================================================================================
JUDGE1_PROMPT = """ROLE: judge 1 of 3, requirement-to-probe fidelity. You vote ALONE. You do
not know how any other judge voted and must not speculate about it.

You evaluate whether the PROBE is a faithful, complete encoding of what the REQUIREMENT asks for.
You are judging the EXPECTED PROBE, not the candidate implementation: never reason about whether
some model would pass or fail, only about whether this probe asks the right question.

Read the supplied metadata carefully before deciding. Inspect the exact structured probe; do not
trust any natural-language claim about what it supposedly checks. Treat explicit metadata as
authoritative. Check every variable, every coefficient, every coefficient sign, the constraint
sense, right-hand side, checked property, expected value, and coverage.

METADATA AUTHORITY AND ITS LIMITS

The supplied metadata is AUTHORITATIVE for what it explicitly states,
including variable meanings, index domains, index sets, requirement scope,
quantifiers, and fixed-parameter values.

Do not override an explicitly stated fact with an assumption about what a
variable or parameter should mean.

Metadata is authoritative but NOT exhaustive. Silence is not confirmation.

If the metadata does not provide a value required to verify a numeric value,
then that numeric value has not been verified.

Do not treat the absence of a contradiction as evidence that the probe is
correct. Do not treat the absence of information as evidence that the probe
is wrong. Report the value as unverifiable.

Do not introduce an interpretation that conflicts with explicit metadata.

Check, in order:
  1. missing fields the template requires
  2. wrong variables (a family the requirement does not constrain)
  3. coefficients that do not follow from the requirement
  4. operator / sense direction
  5. right-hand side value
  6. scope and quantifier (a "for every i" rule must not become one global statement)
  7. incomplete indexed-family coverage (every required member expanded as its own row)
  8. unsupported added content (constraints the requirement never imposes)

ORIGINAL REQUIREMENT ({rid}, category {rcat}):
{rtext}

VISIBLE REQUIREMENT METADATA (variable meanings, index domains, fixed parameters, scope):
{metadata}

TEMPLATE SEMANTICS for the template used:
{template_semantics}

GENERATED STRUCTURED PROBE (before deterministic normalization and compilation):
{structured_probe}

Vote ACCEPT only with the canonical no-change patch (empty arrays and null replacements) below.
If any patch field is non-empty, the verdict MUST be REPAIR; never return ACCEPT with a change.
Vote REPAIR only when you can provide at least one
exact structured change. A statement such as "the coefficients are incorrect" is invalid unless
the patch names the variable and exact replacement coefficient. If the mathematical question must
be replaced, return REPAIR and state the exact required replacement.

PATCH SCHEMA:
{patch_schema}

Return ONLY this JSON object:
{{"requirement_id":"{rid}","judge":"requirement_probe_fidelity",
  "verdict":"ACCEPT" or "REPAIR",
  "patch":<object exactly matching PATCH SCHEMA>,
  "reason":"<exact failure and what must remain unchanged>","confidence":0.0}}"""

JUDGE1_ALLOWED = ("rid", "rcat", "rtext", "metadata", "template_semantics",
                  "structured_probe", "patch_schema")


def _judge1_llm(call_json, req, abstract, executable, metadata, *,
                seed_for, audit) -> Dict[str, Any]:
    """Judge 1: requirement -> probe fidelity. Judges the EXPECTED PROBE, not the candidate."""
    rid = str(req.get("requirement_id", ""))
    template = str(executable.get("template", executable.get("probe_template", "")))
    fields = {"rid": rid, "rcat": req.get("category", ""),
              "rtext": req.get("requirement_text", ""),
              "metadata": pmeta.render(metadata or {}),
              "template_semantics": pmeta.TEMPLATE_SEMANTICS.get(
                  template, "(template semantics unavailable)"),
              "structured_probe": _compact(executable), "patch_schema": PATCH_SCHEMA_TEXT}
    if metadata:
        pmeta.assert_no_oracle_fields(metadata)
    rec = prt.audit_inputs("judge1_requirement_probe_fidelity", fields, JUDGE1_ALLOWED, rid)
    prt.assert_leak_free(rec)
    audit.append(rec)
    obj, err, _ = call_json(JUDGE1_PROMPT.format(**fields), seed_for(rid, "judge1", 0), 900)
    return _normalize_vote(obj, "requirement_probe_fidelity", err, rid)


# =============================================================================================
# JUDGE 2
# =============================================================================================
JUDGE2_PROMPT = """ROLE: judge 2 of 3, mathematical correctness. You vote ALONE and do not know
any other judge's vote.

Read the supplied metadata carefully before deciding. Inspect the exact structured probe rather
than trusting a natural-language description. Explicit metadata is authoritative. Check every
variable and coefficient, every coefficient sign, the relation/operator, right-hand side,
quantifier, aggregation, index scope, checked property, expected value, and coverage. Do not
introduce an interpretation that conflicts with explicit metadata.

Judge mathematical meaning, not exact wording.

Treat mathematically equivalent expressions as equivalent:
- 1 and 1.0
- x <= 1 and "x has upper bound 1"
- "minimize cost" and "cost is minimized"

Do not return REPAIR for a more explicit reconstruction when it only names
variables or categories grounded in visible metadata.

To verify parameters.rhs or any coefficient, you must be able to trace the
number to a value supplied in fixed_parameters or to an explicit derivation
supported by the metadata.

If the number cannot be traced, it is unverifiable. It must not be classified
as correct or incorrect without supporting evidence.

You have no candidate source code beyond the structure shown, no solver result, and no information
about whether this model is correct.

REQUIREMENT ({rid}): {rtext}
VISIBLE METADATA: {metadata}
GENERATED STRUCTURED PROBE (before deterministic normalization and compilation):
{structured_probe}

ACCEPT requires the canonical no-change patch below. REPAIR requires at least one exact
structured change.
If any patch field is non-empty, the verdict MUST be REPAIR; never return ACCEPT with a change.
Vague repair prose is invalid. If the mathematical question must be replaced, return REPAIR with
the exact required replacement. PATCH SCHEMA:
{patch_schema}

Return ONLY this JSON object:
{{"requirement_id":"{rid}","judge":"mathematical_correctness",
  "verdict":"ACCEPT" or "REPAIR",
  "patch":<object exactly matching PATCH SCHEMA>,
  "reason":"<exact failure and what must remain unchanged>","confidence":0.0}}"""

JUDGE2_ALLOWED = ("rid", "rtext", "metadata", "structured_probe", "patch_schema")


def _judge2_llm(call_json, req, abstract, executable, metadata=None, *,
                seed_for, audit) -> Dict[str, Any]:
    rid = str(req.get("requirement_id", ""))
    fields = {"rid": rid, "rtext": req.get("requirement_text", ""),
              "metadata": pmeta.render(metadata or {}),
              "structured_probe": _compact(executable), "patch_schema": PATCH_SCHEMA_TEXT}
    rec = prt.audit_inputs("judge2_mathematical_correctness", fields, JUDGE2_ALLOWED, rid)
    prt.assert_leak_free(rec)
    audit.append(rec)
    obj, err, _ = call_json(JUDGE2_PROMPT.format(**fields), seed_for(rid, "judge2", 0), 800)
    return _normalize_vote(obj, "mathematical_correctness", err, rid)




# =============================================================================================
# JUDGE 3
# =============================================================================================
JUDGE3_PROMPT = """ROLE: judge 3 of 3, claim-to-executable equivalence reviewer. You vote ALONE
and do not know any other judge's vote.

Compare the ORIGINAL REQUIREMENT and GENERATED CLAIM against the EXACT FINAL NORMALIZED EXECUTABLE
PROBE. The executable probe is the exact object that will run. Decide whether all three express
the same mathematical rule.

Check every:
- variable and variable family;
- coefficient and coefficient sign;
- relation/operator;
- right-hand side and constant;
- index and index domain;
- conditional or implication branch;
- quantifier and scope;
- indexed-family member and coverage requirement;
- for objective_difference_probe, the resolved required_objective: its sense, every term's
  variable and numeric coefficient, and the constant. Each coefficient must be a concrete
  number that matches the requirement and the supplied data. An unresolved, symbolic, or
  wrong coefficient requires REPAIR.

Mathematically equivalent rearrangements are acceptable only when signs are transformed correctly.
For example, claim 0.2I + 0.4II = own + external is NOT equivalent to executable expression
0.2I + 0.4II + own + external = 0; that mismatch requires REPAIR.

You have no candidate source code, solver result, expected verdict, mutation identity, or gold
solution. Judge only mathematical equivalence.

ORIGINAL REQUIREMENT ({rid}, category {rcat}):
{rtext}

VISIBLE METADATA (so you can tell a grounded name from an invented one):
{metadata}

GENERATED CLAIM:
{claim}

EXACT FINAL NORMALIZED EXECUTABLE PROBE:
{structured_probe}

Vote ACCEPT only when the requirement, claim, and executable probe are mathematically consistent.
Any mismatch must be REPAIR with the exact required change. Explicit metadata is authoritative;
do not introduce a conflicting interpretation.

ACCEPT requires the canonical no-change patch below. REPAIR requires an exact structured change
using this
schema (use the exact replacement value; never guess an unseen current value):
If any patch field is non-empty, the verdict MUST be REPAIR; never return ACCEPT with a change.
{patch_schema}

Return ONLY this JSON object:
{{"requirement_id":"{rid}","judge":"executable_equivalence",
  "verdict":"ACCEPT" or "REPAIR",
  "patch":<object exactly matching PATCH SCHEMA>,
  "reason":"<exact failure and what must remain unchanged>","confidence":0.0}}"""

JUDGE3_ALLOWED = (
    "rid", "rcat", "rtext", "metadata", "claim", "structured_probe", "patch_schema")


def _judge3_executable_equivalence(call_json, req, claim, executable, metadata, *,
                                   seed_for, audit) -> Dict[str, Any]:
    """Judge 3: compare the generated claim with the exact executable probe."""
    rid = str(req.get("requirement_id", ""))
    fields = {"rid": rid, "rcat": req.get("category", ""),
              "rtext": req.get("requirement_text", ""),
              "metadata": pmeta.render(metadata or {}),
              "claim": str(claim or ""),
              "structured_probe": _compact(executable),
              "patch_schema": PATCH_SCHEMA_TEXT}
    if metadata:
        pmeta.assert_no_oracle_fields(metadata)
    rec = prt.audit_inputs("judge3_executable_equivalence", fields, JUDGE3_ALLOWED, rid)
    prt.assert_leak_free(rec)
    audit.append(rec)
    obj, err, _ = call_json(JUDGE3_PROMPT.format(**fields), seed_for(rid, "judge3", 0), 900)
    return _normalize_vote(obj, "executable_equivalence", err, rid)


# =============================================================================================
# shared vote normalisation
# =============================================================================================
def _normalize_vote(obj, judge: str, error: str, rid: str) -> Dict[str, Any]:
    """Enforce the ACCEPT/REPAIR patch contract."""
    if not isinstance(obj, dict) or str(obj.get("verdict", "")).upper() not in prt.VERDICTS:
        return {"judge": judge, "verdict": TECHNICAL_ERROR, "problem_fields": [],
                "patch": empty_patch(), "instruction": "",
                "reason": "judge response was not valid decision JSON; retry technically",
                "confidence": None, "deterministic": False,
                "error": error or "invalid_judge_response"}
    verdict = str(obj["verdict"]).upper()
    patch, patch_error = _normalize_patch(obj.get("patch"))
    reason = str(obj.get("reason", "")).strip()
    contract_error = ""
    original_verdict = verdict
    forced_repair = False
    if patch_error:
        contract_error = patch_error
    elif verdict == ACCEPT and _patch_has_change(patch):
        # This is a substantive contradiction, not a transport/schema failure. Preserve the
        # exact patch as anonymous repair evidence and conservatively block execution this round.
        verdict = REPAIR
        forced_repair = True
    elif verdict == REPAIR and not _patch_has_change(patch):
        contract_error = "repair_requires_at_least_one_exact_change"
    if contract_error:
        return {
            "judge": judge, "verdict": TECHNICAL_ERROR, "problem_fields": [],
            "patch": empty_patch(), "instruction": "",
            "reason": f"invalid judge decision contract: {contract_error}; retry technically",
            "confidence": obj.get("confidence"), "deterministic": False,
            "error": contract_error,
        }
    return {
        "judge": judge, "verdict": verdict,
        "problem_fields": [str(x) for x in (obj.get("problem_fields") or [])],
        "patch": patch,
        "instruction": str(obj.get("instruction", "")),
        "reason": reason,
        "confidence": obj.get("confidence"), "deterministic": False, "error": "",
        "original_verdict": original_verdict,
        "forced_repair": forced_repair,
        "normalization_reason": (
            "accept_with_nonempty_patch_forced_repair" if forced_repair else ""),
    }


# =============================================================================================
# RETAINED PANEL
# =============================================================================================
def panel_version_b(*, call_json, req, payload, abstract, executable,
                    model_structure, seed_for, audit, metadata=None,
                    phase="first_two", claim=""):
    """Run the retained judges in the approved two-stage order."""
    del payload, model_structure
    if phase == "first_two":
        return [
            _judge1_llm(call_json, req, abstract, executable, metadata,
                        seed_for=seed_for, audit=audit),
            _judge2_llm(call_json, req, abstract, executable, metadata,
                        seed_for=seed_for, audit=audit),
        ]
    if phase == "judge3":
        return [
            _judge3_executable_equivalence(
                call_json, req, claim, executable, metadata,
                seed_for=seed_for, audit=audit)
        ]
    raise ValueError(f"unknown judge phase {phase!r}")


PANELS = {VERSION_B: panel_version_b}

DEFAULT_VERSION = VERSION_B


def version_from_env(environ=None) -> str:
    import os
    value = (environ or os.environ).get("EXP2_JUDGE_PANEL", "").strip()
    return value if value in PANELS else DEFAULT_VERSION


def get_panel(version: str) -> Callable:
    if version not in PANELS:
        raise ValueError(f"unknown judge panel version {version!r}; "
                         f"expected one of {sorted(PANELS)}")
    return PANELS[version]
