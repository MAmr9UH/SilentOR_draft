#!/usr/bin/env python3
"""V42 typed probes, staged ACCEPT/REPAIR judging, witness verification, and root adjudication."""
from __future__ import annotations

import json
import os
import copy
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import common_runner as cr
import flow_semantics as fsem
import judge_panels as jpanel
import problem_metadata as pmeta
import probe_forensics as pfor
import probe_schemas as pschema
import probe_roundtrip as prt
import probe_engine as pe
import runtime_context as rctx
import request_identity as reqid
import shadow_witness_architecture as swa
import structural_evidence as se
import track_b_localization as tbl

TRACK = "B"
PROBE_MAX_TOKENS = 6000
CONFIRM_MAX_TOKENS = 6000
TEMPLATE_SELECTOR_MAX_TOKENS = 2400
SHADOW_VERIFIER_MAX_TOKENS = 4800
SHADOW_ROOT_MAX_TOKENS = 4800
MAX_PROBE_ATTEMPTS = 3
MAX_TECHNICAL_RETRIES = 3

PERMANENT_ERROR_MARKERS = (
    "api_key is not set", "sdk is not installed", "context budget", "unknown model",
    "model not found", "invalid api key", "authentication", "permission denied",
    "unsupported parameter", "requires architecture=", "configuration",
)


def _provider_error_kind(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}".lower()
    if any(marker in text for marker in PERMANENT_ERROR_MARKERS):
        return "permanent"
    if (isinstance(exc, (TimeoutError, ConnectionError, OSError)) or
            any(marker in text for marker in (
                "timeout", "temporar", "connection", "server error", "http 429",
                "http 500", "http 502", "http 503", "http 504", "rate limit"))):
        return "retryable"
    return "permanent"


def _unresolved_requirement_label(technical_failure: bool) -> str:
    """Every requirement-local failure is unresolved, never a candidate pipeline error."""
    del technical_failure
    return "UNRESOLVED"


def _aggregate_candidate_verdict(confirmed_failure_ids: Iterable[str]) -> str:
    """Apply original V42 aggregation; fatal exceptions are handled by the runner."""
    return "incorrect" if list(confirmed_failure_ids) else "correct"


def _systemic_requirement_failure(total_requirements: int,
                                   technical_failures: int) -> bool:
    """Identify a pervasive stage collapse without promoting isolated failures."""
    return (int(total_requirements) >= 3 and
            int(technical_failures) * 10 >= int(total_requirements) * 9)

TAXONOMY = ("constraint_omission, constraint_misspecification, domain_or_bound_error, "
            "linking_or_logic_error, objective_accounting_error, "
            "extra_or_overrestrictive_constraint, mixed_or_unclear, none")


# ---------------------------------------------------------------------------------------------
# Stable ROLE markers. Every prompt begins with "ROLE: <marker>". Tests, stubs, and any prompt
# dispatch match on these constants -- never on prose -- so prompt wording can be revised without
# breaking anything downstream.
# ---------------------------------------------------------------------------------------------
ROLE_PROBE_GENERATOR = "probe generator"
ROLE_TEMPLATE_SELECTOR = "probe template selector"

TEMPLATE_SELECTOR_STABLE_PREFIX = """ROLE: probe template selector.

Select exactly one compatible probe template for the supplied requirement. You select a
mathematical question type; you do not write the probe, inspect an execution result, or decide
whether a candidate is correct.

Every requirement receives the same ALLOWED_TEMPLATES. Select from mathematical structure, never
from keywords or the category label. One aggregate equation or inequality, including a sum over
several variables, is one linear_requirement_probe. Use indexed_constraint_family_probe only when
the requirement imposes separate member-specific constraints over an authoritative index set.
Use implication_probe only for genuine conditional logic and check_variable_property only for a
declared variable property. Explicit metadata is authoritative. Account for prior attempts and
their format, validation, or repair reasons.
"""

TEMPLATE_SELECTOR_SUFFIX = """
REQUIREMENT:
{rid}: {rtext} [category={rcat}]

AUTHORITATIVE REQUIREMENT METADATA:
{metadata}

ALLOWED_TEMPLATES:
{allowed}

TEMPLATE SEMANTICS:
{guide}

PRIOR ATTEMPT HISTORY:
{history}

Return only:
{{"selected_template":"one exact ALLOWED_TEMPLATES value",
  "reason":"short compatibility explanation"}}
"""

TEMPLATE_SELECTOR_PROMPT = TEMPLATE_SELECTOR_STABLE_PREFIX + TEMPLATE_SELECTOR_SUFFIX

PROBE_GENERATOR_STABLE_PREFIX = """ROLE: probe generator. You produce ONE executable verification probe for ONE
requirement. You do NOT judge the candidate model, you do NOT return a verdict, and nothing you
write decides whether the candidate is correct or incorrect. A deterministic solver makes that
decision later from your probe.

SOURCE OF TRUTH (mandatory):
- Every expected value -- relation direction/sense, right-hand side, bounds, coefficients,
  objective direction, expected property values -- must be derived from the REQUIREMENT text,
  RELEVANT DATA, and AUTHORITATIVE REQUIREMENT METADATA.
- MODEL_SLICE shows what the candidate model happens to contain. It supplies variable NAMES ONLY.
  Never copy a number, bound, sense, or coefficient out of MODEL_SLICE: doing so would test the
  candidate against itself, and deterministic validation will block the probe.

Read AUTHORITATIVE REQUIREMENT METADATA carefully. It is the same candidate-independent metadata
shown to the judges. Its explicit variable/index meanings, domains, fixed-parameter values, units,
time periods, scope, quantifiers, and constraint semantics are authoritative. Silence is not
confirmation; never invent an unstated number.

Judges 1 and 2 review the generated probe before normalization and compilation. After deterministic
normalization and compilation, Judge 3 compares your claim with the exact executable probe. Every
judge returns only ACCEPT or REPAIR. A repair returns an exact structured patch. You get at most
{max_attempts} attempts.

Choose only from ALLOWED_TEMPLATES. Use only exact variable names or prefixes from MODEL_SLICE.
Never write Python.

FULL PROBLEM DESCRIPTION/NARRATIVE:
{description}

RELEVANT DATA:
{data}
"""

PROBE_GENERATOR_SUFFIX = """
REQUIREMENT:
{rid}: {rtext} [category={rcat}]

AUTHORITATIVE REQUIREMENT METADATA:
{metadata}

MODEL_SLICE (observed candidate names and values -- names are usable, values are NOT normative):
{inventory}

ALLOWED_TEMPLATES: {allowed}
{guide}

If the requirement cannot be expressed by any allowed template, return probe_template
"not_probeable". That is an honest, penalty-free answer and can never make the candidate fail.

Return only:
{{"probe_id":"descriptive_name","requirement_id":"{rid}",
 "probe_template":"approved template","claim":"what is tested","parameters":{{}}}}
{attempt_note}
"""

PROBE_PROMPT = PROBE_GENERATOR_STABLE_PREFIX + PROBE_GENERATOR_SUFFIX


class _Ledger:
    def __init__(self):
        self.raws: List[str] = []
        self.calls: List[Dict[str, Any]] = []
        self.input_tokens = 0
        self.output_tokens = 0
        self.runtime = 0.0

    def add(self, response: Dict[str, Any]) -> None:
        self.raws.append(response.get("text", ""))
        self.calls.append(response.get("call_metadata", {}))
        self.input_tokens += int(response.get("input_tokens", 0) or 0)
        self.output_tokens += int(response.get("output_tokens", 0) or 0)
        self.runtime += float(response.get("runtime_sec", 0.0) or 0.0)


def _call_json(model: str, prompt: str, ledger: _Ledger, *, seed, temperature,
               ollama_url: str, max_tokens: int, num_ctx=None,
               require_think_disabled=False, response_schema=None,
               response_schema_name=None, stage="unknown",
               problem_id=None, candidate_id=None, requirement_id=None,
               attempt=None, technical_retry=None, stable_prefix="", role="",
               context_safety_tokens=1024) -> Tuple[
                   Optional[Dict[str, Any]], str, Dict[str, Any]]:
    budget = rctx.assert_prompt_fits(
        prompt, num_predict=int(max_tokens), num_ctx=num_ctx,
        safety_tokens=int(context_safety_tokens),
        label=f"{stage}:{candidate_id or ''}:{requirement_id or ''}")
    response = cr.call_model(model, prompt, temperature=temperature, seed=seed,
                             num_predict=max_tokens, ollama_url=ollama_url,
                             num_ctx=num_ctx,
                             require_think_disabled=require_think_disabled,
                             response_schema=response_schema,
                             response_schema_name=response_schema_name,
                             call_context={
                                 "pipeline_stage": stage,
                                 "problem_id": problem_id,
                                 "candidate_id": candidate_id,
                                 "requirement_id": requirement_id,
                                 "pipeline_attempt": attempt,
                                 "semantic_attempt": attempt,
                                 "technical_retry": technical_retry,
                                 "role": role or stage,
                                 "stable_prefix": stable_prefix,
                                 **budget,
                             })
    ledger.add(response)
    obj, error = cr.extract_json(response.get("text", ""))
    if response.get("truncated"):
        error = "truncated_response"
    elif not response.get("text", "").strip():
        call_metadata = response.get("call_metadata", {}) or {}
        visible_kind = (
            "empty_visible_response_after_generation"
            if int(call_metadata.get("eval_count", 0) or 0) > 0 else
            "zero_output_token_response")
        error = (
            f"{visible_kind}:done_reason={call_metadata.get('done_reason', '')}:"
            f"think_honored={call_metadata.get('think_honored', '')}")
    return (obj if isinstance(obj, dict) else None), error or "", response


def _call_json_with_technical_retries(
        model: str, prompt: str, ledger: _Ledger, *, seed, temperature,
        ollama_url: str, max_tokens: int,
        accept: Optional[Callable[[Optional[Dict[str, Any]]], str]] = None,
        max_retries: int = MAX_TECHNICAL_RETRIES, **kwargs
) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any], List[Dict[str, Any]]]:
    """Retry malformed, empty, truncated, or contract-invalid output technically.

    These retries never consume one of the three semantic probe attempts.
    """
    records: List[Dict[str, Any]] = []
    last_obj: Optional[Dict[str, Any]] = None
    last_error = ""
    last_response: Dict[str, Any] = {}
    for retry_index in range(int(max_retries)):
        # A technical retry is the same request, not a new stochastic experiment.
        call_seed = seed
        try:
            obj, error, response = _call_json(
                model, prompt, ledger, seed=call_seed, temperature=temperature,
                ollama_url=ollama_url, max_tokens=max_tokens,
                technical_retry=retry_index + 1, **kwargs)
        except Exception as exc:
            if _provider_error_kind(exc) == "permanent":
                raise RuntimeError(
                    f"permanent_configuration_or_provider_error:{type(exc).__name__}:{exc}") from exc
            obj, response = None, {"text": "", "call_metadata": {
                "technical_retry": retry_index + 1,
                "provider_error_kind": "retryable", "provider_error": str(exc)}}
            error = f"retryable_provider_error:{type(exc).__name__}:{exc}"
        contract_error = accept(obj) if not error and accept is not None else ""
        combined_error = error or contract_error
        records.append({
            "technical_retry": retry_index + 1,
            "error": combined_error,
            "completion_status": response.get("completion_status", ""),
            "done_reason": (response.get("call_metadata") or {}).get("done_reason", ""),
            "call_metadata": response.get("call_metadata", {}),
        })
        last_obj, last_error, last_response = obj, combined_error, response
        if not combined_error:
            return obj, "", response, records
    return last_obj, (
        f"technical_retry_exhausted:{last_error or 'invalid_structured_response'}"
    ), last_response, records


def _attempt1_cached_call(*, cache, stage: str, prompt: str, response_schema,
                          model: str, role: str, seed, temperature,
                          output_token_limit: int, provider_options: Dict[str, Any],
                          stage_inputs: Dict[str, Any], semantic_attempt: int,
                          candidate_id: Optional[str], record_id: str, invoke):
    """Reuse only exact, valid Attempt-1 model artifacts; never reuse validation/execution."""
    identity = reqid.request_identity(
        stage=stage, prompt=prompt, response_schema=response_schema, model=model, role=role,
        seed=seed, temperature=temperature, output_token_limit=output_token_limit,
        provider_options=provider_options, stage_inputs=stage_inputs)
    if cache is not None and int(semantic_attempt) == 1 and identity["cache_key"] in cache:
        cached = cache[identity["cache_key"]]
        provenance = reqid.reuse_record(
            identity, cached, receiver_candidate=str(candidate_id or ""),
            receiver_record=record_id)
        response = {
            "text": cached.get("raw_response", ""), "input_tokens": 0,
            "output_tokens": 0, "runtime_sec": 0.0, "truncated": False,
            "completion_status": "reused_attempt_1_artifact", "incomplete_reason": "",
            "call_metadata": {**provenance, "model": model, "role": role,
                              "candidate_id": candidate_id, "semantic_attempt": 1,
                              "technical_retry": 0,
                              "provider_cache_status": "not_a_provider_call"},
        }
        return copy.deepcopy(cached.get("object")), "", response, [], provenance

    obj, error, response, technical_records = invoke()
    provenance = reqid.generated_record(
        identity, candidate=str(candidate_id or ""), record=record_id)
    if cache is not None and int(semantic_attempt) == 1 and not error and isinstance(obj, dict):
        cache[identity["cache_key"]] = {
            "object": copy.deepcopy(obj), "raw_response": response.get("text", ""),
            "source_candidate": str(candidate_id or ""), "source_record": record_id,
            "identity": identity,
        }
    return obj, error, response, technical_records, provenance


def _probe_prompt(payload: Dict[str, Any], req: Dict[str, Any], slice_: Dict[str, Any],
                  allowed: Iterable[str], metadata: Dict[str, Any],
                  attempt_note: str = "") -> str:
    allowed = list(allowed)
    return PROBE_PROMPT.format(
        description=str(payload.get("problem_description", "")),
        data=json.dumps(payload.get("data_instance", {}), ensure_ascii=False,
                        separators=(",", ":")),
        rid=req["requirement_id"], rtext=req["requirement_text"],
        rcat=req.get("category", ""),
        metadata=pmeta.render(metadata),
        inventory=json.dumps(slice_, ensure_ascii=False, separators=(",", ":")),
        allowed=", ".join(allowed), guide=pe.template_guide(allowed),
        max_attempts=MAX_PROBE_ATTEMPTS,
        attempt_note=("REPAIR/ALTERNATE INSTRUCTION: " + attempt_note if attempt_note else ""),
    )


def _selector_prompt(payload: Dict[str, Any], req: Dict[str, Any],
                     slice_: Dict[str, Any], allowed: Iterable[str],
                     metadata: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
    allowed = list(allowed)
    return TEMPLATE_SELECTOR_PROMPT.format(
        rid=req["requirement_id"], rtext=req["requirement_text"],
        rcat=req.get("category", ""),
        metadata=pmeta.render(metadata),
        allowed=", ".join(allowed),
        guide=pe.template_guide(allowed),
        history=json.dumps(history, ensure_ascii=False, separators=(",", ":"),
                           default=str),
    )


def _panel_gate(payload, req, probe, model_structure, panel_version, model, ledger, *,
                seed=None, temperature=None, ollama_url=None, max_tokens=800,
                phase="first_two", claim="", metadata=None, num_ctx=None,
                require_think_disabled=False, candidate_id=None,
                semantic_attempt=None, attempt1_cache=None, reuse_records=None,
                context_safety_tokens=1024):
    """Run one ACCEPT/REPAIR judge stage in the approved two-stage order."""
    def _call(prompt, call_seed, tokens):
        if prompt.startswith("ROLE: judge 1"):
            stage = "judge_1_fidelity"
        elif prompt.startswith("ROLE: judge 2"):
            stage = "judge_2_mathematical"
        elif prompt.startswith("ROLE: judge 3"):
            stage = "judge_3_executable_equivalence"
        else:
            stage = "three_judge_panel"
        stable_prefix = {
            "judge_1_fidelity": jpanel.JUDGE1_PROMPT.split("ORIGINAL REQUIREMENT", 1)[0],
            "judge_2_mathematical": jpanel.JUDGE2_PROMPT.split("REQUIREMENT (", 1)[0],
            "judge_3_executable_equivalence": jpanel.JUDGE3_PROMPT.split(
                "ORIGINAL REQUIREMENT", 1)[0],
        }.get(stage, prompt.split("\n\n", 1)[0])
        rid = str(req.get("requirement_id", ""))
        schema = None
        schema_name = stage
        expected_name = ""
        if stage.startswith("judge_"):
            expected_name = {
                "judge_1_fidelity": "requirement_probe_fidelity",
                "judge_2_mathematical": "mathematical_correctness",
                "judge_3_executable_equivalence": "executable_equivalence",
            }.get(stage, "")
            schema = pschema.judge_decision_schema(rid, expected_name)

        request_tokens = max(int(tokens), int(max_tokens))
        identity = reqid.request_identity(
            stage=stage, prompt=prompt, response_schema=schema, model=model, role=stage,
            seed=call_seed, temperature=temperature, output_token_limit=request_tokens,
            provider_options={"ollama_num_ctx": num_ctx,
                              "require_think_disabled": require_think_disabled},
            stage_inputs={"problem_id": payload.get("problem_id"),
                          "requirement_id": rid,
                          "visible_request_sha256": reqid.sha256_text(prompt)})
        record_id = f"{rid}:attempt{semantic_attempt}:{stage}"
        if (attempt1_cache is not None and int(semantic_attempt or 0) == 1 and
                identity["cache_key"] in attempt1_cache):
            cached = attempt1_cache[identity["cache_key"]]
            provenance = reqid.reuse_record(
                identity, cached, receiver_candidate=str(candidate_id or ""),
                receiver_record=record_id)
            if reuse_records is not None:
                reuse_records.append(provenance)
            return copy.deepcopy(cached.get("object")), "", {
                "text": cached.get("raw_response", ""), "input_tokens": 0,
                "output_tokens": 0, "runtime_sec": 0.0,
                "completion_status": "reused_attempt_1_artifact",
                "call_metadata": {**provenance, "model": model, "role": stage,
                                  "candidate_id": candidate_id,
                                  "requirement_id": rid, "semantic_attempt": 1,
                                  "technical_retry": 0,
                                  "provider_cache_status": "not_a_provider_call"},
            }
        provenance = reqid.generated_record(
            identity, candidate=str(candidate_id or ""), record=record_id)
        if reuse_records is not None:
            reuse_records.append(provenance)
        last_obj, last_error, last_response = None, "", {}
        for technical_retry in range(MAX_TECHNICAL_RETRIES):
            retry_seed = call_seed
            try:
                response = cr.call_model(
                    model, prompt, seed=retry_seed, temperature=temperature,
                    num_predict=request_tokens, ollama_url=ollama_url,
                    num_ctx=num_ctx, require_think_disabled=require_think_disabled,
                    response_schema=schema, response_schema_name=schema_name,
                    call_context={
                    "pipeline_stage": stage,
                    "technical_retry": technical_retry + 1,
                    "semantic_attempt": semantic_attempt,
                    "role": stage,
                    "stable_prefix": stable_prefix,
                    "problem_id": payload.get("problem_id"),
                    "candidate_id": candidate_id,
                    "requirement_id": rid,
                    **rctx.assert_prompt_fits(
                        prompt, num_predict=request_tokens, num_ctx=num_ctx,
                        safety_tokens=int(context_safety_tokens), label=stage),
                    })
            except Exception as exc:
                if _provider_error_kind(exc) == "permanent":
                    raise RuntimeError(
                        f"permanent_configuration_or_provider_error:"
                        f"{type(exc).__name__}:{exc}") from exc
                last_obj, last_error, last_response = None, (
                    f"retryable_provider_error:{type(exc).__name__}:{exc}"), {
                    "text": "", "call_metadata": {
                        "technical_retry": technical_retry + 1,
                        "provider_error_kind": "retryable", "provider_error": str(exc)}}
                continue
            ledger.add(response)
            obj, parse_error = cr.extract_json(response.get("text", ""))
            obj = obj if isinstance(obj, dict) else None
            if response.get("truncated"):
                parse_error = "truncated_response"
            elif not response.get("text", "").strip():
                parse_error = "empty_structured_response"
            contract_error = ""
            if not parse_error and stage.startswith("judge_"):
                normalized = jpanel._normalize_vote(obj, expected_name, "", rid)
                contract_error = str(normalized.get("error", ""))
            last_obj, last_error, last_response = obj, (
                parse_error or contract_error or ""), response
            if not last_error:
                if attempt1_cache is not None and int(semantic_attempt or 0) == 1:
                    attempt1_cache[identity["cache_key"]] = {
                        "object": copy.deepcopy(obj), "raw_response": response.get("text", ""),
                        "source_candidate": str(candidate_id or ""),
                        "source_record": record_id, "identity": identity,
                    }
                return obj, "", response
        return last_obj, (
            f"technical_retry_exhausted:{last_error or 'invalid_response'}"
        ), last_response

    def _seed_for(rid, stage, index):
        return cr.derive_seed(seed, TRACK, "panel", panel_version, rid, stage, index)

    common = {
        "call_json": _call, "req": req, "payload": payload, "probe": probe,
        "model_structure": model_structure, "panel": jpanel.get_panel(panel_version),
        "seed_for": _seed_for, "metadata": metadata,
    }
    if phase == "first_two":
        return prt.judge_generated_probe_first_two(**common)
    if phase == "judge3":
        return prt.judge_final_probe_third(**common, claim=claim)
    raise ValueError(f"unknown judge phase {phase!r}")


def _blank_accounting(error: str = "", *,
                      semantic_validation_mode: str = "enforce") -> Dict[str, Any]:
    return {
        "architecture": swa.ARCHITECTURE_NAME,
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
        "runtime_sec": 0.0, "solver_calls": 0, "truncated": False,
        "parse_ok": False, "prediction_valid": False,
        "validation_errors": error, "error": error,
        "raw_responses": [], "call_metadata": [],
        "probes_generated": 0, "probes_valid": 0, "probes_unknown": 0,
        "probes_executed": 0, "probe_log": [],
        "executed_fail_count": 0, "executed_fail_requirement_ids": [],
        "requirement_result_labels": {}, "official_requirement_result_labels": {},
        "decision_sources": {}, "pipeline_error_count": 1,
        "unresolved_requirement_count": 0, "evaluation_complete": False,
        "semantic_validation_mode": semantic_validation_mode,
        "primary_suspected_requirement_id": None,
        "root_cause_requirement_ids": [], "collateral_requirement_ids": [],
        "localization_evidence": [], "enforced_final_verdict": "pipeline_error",
        "decision_mode": "pipeline_error", "probe_attempted": False,
        "probe_attempt_records": [], "deterministic_evidence_records": {},
        "unresolved_requirement_ids": [], "requirement_summaries": [],
        "attempt_counts": {}, "execution_modes": {}, "diagnostic_only_ids": [],
        "diagnostic_fail_requirement_ids": [], "raw_fail_requirement_ids": [],
        "authoritative_declared_attribute_fail_requirement_ids": [],
        "authoritative_declared_attribute_fail_count": 0,
        "witness_reviewable_fail_requirement_ids": [],
        "official_retained_fail_requirement_ids": [],
        "official_witness_policy": "probe_aware_root",
        "current_ranked_requirement_ids": [],
        "witness_probe_aware_records": {}, "witness_verifier_skip_records": {},
        "witness_probe_aware_call_count": 0, "root_cause_record": {},
        "root_cause_call_count": 0, "inference_stage_failure_counts": {},
    }

def verify(payload, model, *, problem_record=None, gold_objective=None, audit_module=None,
           num_predict=None, temperature=None, seed=None,
           ollama_url="http://localhost:11434/api/generate",
           candidate_id=None, ollama_num_ctx=None, require_think_disabled=False,
           context_safety_tokens=1024,
           smoke_requirement_id=None, smoke_fail_fast=False,
           probe_num_predict=PROBE_MAX_TOKENS,
           semantic_num_predict=CONFIRM_MAX_TOKENS,
           witness_verifier_num_predict=SHADOW_VERIFIER_MAX_TOKENS,
           judge_panel=jpanel.VERSION_B,
           attempt_record_path=None,
           architecture=swa.ARCHITECTURE_NAME,
           root_cause_num_predict=SHADOW_ROOT_MAX_TOKENS,
           requirement_scope_ids=None, attempt1_cache=None,
           semantic_validation_mode="enforce"):
    """Verify every active requirement without gold objectives, hidden audits, or oracle probes."""
    del gold_objective, audit_module, num_predict
    import requirement_provider as rp

    if architecture != swa.ARCHITECTURE_NAME:
        raise ValueError(f"V42 requires architecture={swa.ARCHITECTURE_NAME}")
    if judge_panel not in jpanel.PANELS:
        raise ValueError(f"Track B requires one of the three-judge panels: "
                         f"{sorted(jpanel.PANELS)}")
    if semantic_validation_mode not in {"enforce", "log-only", "off"}:
        raise ValueError(
            "semantic_validation_mode must be enforce, log-only, or off")
    data = dict(payload.get("data_instance", {}))
    inventory = pe.introspect(payload["candidate_code"], data)
    if "error" in inventory:
        pred = {"verdict": "pipeline_error", "suspected_requirement_ids": [],
                "predicted_taxonomy_category": "none",
                "error_reason": f"candidate introspection failed: {inventory['error']}",
                "evidence": "", "confidence": 0.0}
        return pred, _blank_accounting(
            inventory["error"], semantic_validation_mode=semantic_validation_mode)

    requirements = list(payload["requirements"])
    all_requirement_ids = [str(item["requirement_id"]) for item in requirements]
    if requirement_scope_ids is not None:
        requested_scope = list(dict.fromkeys(str(value) for value in requirement_scope_ids))
        unknown_scope = [rid for rid in requested_scope if rid not in set(all_requirement_ids)]
        if unknown_scope:
            raise ValueError(f"unknown requirement_scope_ids: {unknown_scope}")
        requirements = [item for item in requirements
                        if str(item["requirement_id"]) in set(requested_scope)]
    if smoke_requirement_id is not None:
        requirements = [r for r in requirements if r["requirement_id"] == smoke_requirement_id]
        if not requirements:
            raise ValueError(f"smoke requirement {smoke_requirement_id} is not supplied")

    ledger = _Ledger()
    probe_log: List[Dict[str, Any]] = []
    result_labels: Dict[str, str] = {}
    decision_sources: Dict[str, str] = {}
    validation_errors: List[str] = []
    solver_calls = probes_generated = probes_valid = probes_unresolved = probes_executed = 0
    semantic_calls = fallback_count = requirement_technical_failures = 0
    retried = False
    panel_records: List[Dict[str, Any]] = []
    reuse_records: List[Dict[str, Any]] = []
    panel_repair_used: Dict[str, bool] = {}
    panel_actions: Dict[str, str] = {}
    panel_decisions: Dict[str, str] = {}
    panel_judge_log: List[Dict[str, Any]] = []
    execution_modes: Dict[str, str] = {}
    fallback_metadata: Dict[str, Any] = {}
    attempt_counts: Dict[str, int] = {}
    panel_leak_violations: List[str] = []
    probe_attempt_records: List[Dict[str, Any]] = []
    deterministic_evidence_records: Dict[str, Dict[str, Any]] = {}
    requirement_summaries: List[Dict[str, Any]] = []

    metadata_problem = dict(problem_record or {})
    metadata_problem.setdefault("problem_type", payload.get("problem_type", ""))
    metadata_problem.setdefault("question", payload.get("problem_description", ""))
    metadata_problem.setdefault("problem_description", payload.get("problem_description", ""))
    metadata_problem.setdefault("data_instance", payload.get("data_instance", {}))

    def _checkpoint(record: Dict[str, Any], stage: str) -> None:
        """Crash-safe append-only snapshots; the final result field remains authoritative."""
        if not attempt_record_path:
            return
        path = Path(attempt_record_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        snapshot = {"checkpoint_stage": stage, **record}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot, ensure_ascii=False, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def _finish_attempt(entry: Dict[str, Any], record: Dict[str, Any], route: str) -> None:
        if not record.get("judge_decisions"):
            technical_stage = str(record.get("technical_stage", ""))
            not_run_reason = (
                f"judges not run because {technical_stage} exhausted technical retries"
                if technical_stage else
                "judges not run because this attempt ended before panel authorization")
            record["judge_decisions"] = [
                {"judge": name, "verdict": "NOT_RUN", "patch": jpanel.empty_patch(),
                 "reason": not_run_reason}
                for name in ("requirement_probe_fidelity", "mathematical_correctness",
                             "executable_equivalence")
            ]
            record["judge_patches"] = [
                {"judge": item["judge"], "patch": item["patch"]}
                for item in record["judge_decisions"]
            ]
        if not record.get("panel_action"):
            record["panel_action"] = "NOT_RUN"
        record["final_route"] = route
        if record not in entry["attempts"]:
            entry["attempts"].append(record)
        _checkpoint(record, "finalized")

    def _reroute_latest(entry: Dict[str, Any], route: str,
                        fallback_record: Optional[Dict[str, Any]] = None) -> None:
        if not entry.get("attempts"):
            return
        record = entry["attempts"][-1]
        record["final_route"] = route
        if fallback_record is not None:
            record["fallback_record"] = fallback_record
        _checkpoint(record, "routed")

    def _record_judge_stage(rid: str, attempt: int, attempt_record: Dict[str, Any],
                            panel_record: Dict[str, Any], phase: str) -> Dict[str, Any]:
        judges = [{
            "judge": item.get("judge"), "verdict": item.get("verdict"),
            "deterministic": item.get("deterministic"),
            "problem_fields": item.get("problem_fields", []),
            "patch": item.get("patch", {}), "reason": item.get("reason", ""),
            "error": item.get("error", ""),
            "original_verdict": item.get("original_verdict", item.get("verdict")),
            "forced_repair": bool(item.get("forced_repair", False)),
            "normalization_reason": item.get("normalization_reason", ""),
        } for item in panel_record.get("judges", [])]
        decision = panel_record.get("panel") or {}
        summary = {
            "version": judge_panel, "phase": phase,
            "action": panel_record.get("action"),
            "verdicts": decision.get("verdicts", []),
            "margin": decision.get("margin", ""),
            "pipeline_error": False,
            "requirement_unresolved": bool(panel_record.get("requirement_unresolved")),
            "leak_free": panel_record.get("leak_free", False),
            "judges": judges,
        }
        attempt_record.setdefault("judge_stages", []).append(summary)
        attempt_record.setdefault("judge_decisions", []).extend(judges)
        attempt_record.setdefault("judge_patches", []).extend(
            {"judge": item.get("judge"), "patch": item.get("patch", {})}
            for item in judges)
        all_judges = list(attempt_record.get("judge_decisions", []))
        attempt_record["judge_panel"] = {
            "version": judge_panel, "action": panel_record.get("action"),
            "verdicts": [item.get("verdict") for item in all_judges],
            "margin": decision.get("margin", ""), "judges": all_judges,
            "stages": list(attempt_record.get("judge_stages", [])),
        }
        panel_records.append({"requirement_id": rid, "attempt": attempt,
                              **summary})
        panel_actions[rid] = str(panel_record.get("action", ""))
        panel_decisions[rid] = str(panel_record.get("action", ""))
        for item in judges:
            panel_judge_log.append({"requirement_id": rid, "attempt": attempt,
                                    "phase": phase, **item})
        if not panel_record.get("leak_free", False):
            panel_leak_violations.append(rid)
        return summary

    for req_index, req in enumerate(requirements):
        rid = req["requirement_id"]
        slice_ = pe.requirement_inventory_slice(inventory, req, data)
        compatible = pe.compatible_templates(req)
        req_metadata = pmeta.build_metadata(metadata_problem, req, compatible)
        pmeta.assert_no_oracle_fields(req_metadata)
        fallback_metadata[rid] = req_metadata
        attempt_counts[rid] = 0
        structural_record = se.build_record(inventory, req, req_metadata, slice_)
        deterministic_evidence_records[rid] = structural_record
        entry: Dict[str, Any] = {
            "requirement_id": rid, "category": req.get("category", ""),
            "inventory_sha256": slice_.get("inventory_sha256"),
            "tier1": structural_record,
            "structural_evidence": structural_record,
            "attempts": [],
        }

        # A sufficient structural FAIL is probe-independent evidence.  It must not disappear
        # merely because the generator returned empty/malformed output before the panel could
        # run.  Keep structural PASS probe-first as before; this narrowly repairs FAIL routing
        # and leaves target selection and structural sufficiency rules completely unchanged.
        if structural_record.get("sufficient") and \
                structural_record.get("status") == "FAIL":
            entry.update({
                "result_label": "STRUCTURAL_FAIL",
                "status": "FAIL",
                "decision_source": "structural_witness",
                "execution_result": structural_record,
            })
            result_labels[rid] = "STRUCTURAL_FAIL"
            decision_sources[rid] = "structural_witness"
            probe_log.append(entry)
            continue

        remaining = list(compatible)
        decided = False
        previous_note = ""
        selected_template: Optional[str] = None
        selector_history: List[Dict[str, Any]] = []
        unresolved_technical = False
        for attempt in range(MAX_PROBE_ATTEMPTS):
            allowed_pool = remaining or list(compatible)
            if selected_template not in allowed_pool:
                selector_prompt = _selector_prompt(
                    payload, req, slice_, allowed_pool, req_metadata,
                    selector_history)
                selector_schema = pschema.template_selector_schema(allowed_pool)
                selector_seed = cr.derive_seed(
                    seed, TRACK, rid, req_index, "template_selector", attempt)
                selector_limit = min(TEMPLATE_SELECTOR_MAX_TOKENS, int(probe_num_predict))
                (selector_obj, selector_error, selector_response,
                 selector_technical_calls, selector_reuse) = _attempt1_cached_call(
                    cache=attempt1_cache, stage="template_selector", prompt=selector_prompt,
                    response_schema=selector_schema, model=model, role=ROLE_TEMPLATE_SELECTOR,
                    seed=selector_seed, temperature=temperature,
                    output_token_limit=selector_limit,
                    provider_options={"ollama_num_ctx": ollama_num_ctx,
                                      "require_think_disabled": require_think_disabled},
                    stage_inputs={"problem_id": payload.get("problem_id"),
                                  "requirement_id": rid},
                    semantic_attempt=attempt + 1, candidate_id=candidate_id,
                    record_id=f"{rid}:attempt{attempt + 1}:template_selector",
                    invoke=lambda: _call_json_with_technical_retries(
                        model, selector_prompt, ledger, seed=selector_seed,
                        temperature=temperature, ollama_url=ollama_url,
                        max_tokens=selector_limit, num_ctx=ollama_num_ctx,
                        require_think_disabled=require_think_disabled,
                        response_schema=selector_schema,
                        response_schema_name="track_b_template_selector",
                        accept=lambda value: (
                            "invalid_selected_template"
                            if str((value or {}).get("selected_template", "")) not in allowed_pool
                            else ""),
                        stage="template_selector", problem_id=payload.get("problem_id"),
                        candidate_id=candidate_id, requirement_id=rid, attempt=attempt + 1,
                        stable_prefix=TEMPLATE_SELECTOR_STABLE_PREFIX,
                        role=ROLE_TEMPLATE_SELECTOR,
                        context_safety_tokens=context_safety_tokens))
                reuse_records.append(selector_reuse)
                selected_candidate = str(
                    (selector_obj or {}).get("selected_template", ""))
                selector_record = {
                    "attempt": attempt + 1,
                    "allowed_templates": list(allowed_pool),
                    "selected_template": selected_candidate,
                    "reason": str((selector_obj or {}).get("reason", "")),
                    "error": selector_error,
                    "raw_response": selector_response.get("text", ""),
                    "technical_calls": selector_technical_calls,
                    "reuse": selector_reuse,
                }
                selector_history.append(selector_record)
                if selector_error or selected_candidate not in allowed_pool:
                    unresolved_technical = True
                    requirement_technical_failures += 1
                    technical_record = {
                        "requirement_id": rid,
                        "attempt": attempt_counts[rid] + 1,
                        "semantic_attempt_consumed": False,
                        "technical_stage": "template_selector",
                        "technical_calls": selector_technical_calls,
                        "template_selector": selector_record,
                        "judge_decisions": [],
                        "panel_action": prt.ACTION_TECHNICAL_ERROR,
                        "validator_result": {"ok": False, "reason": selector_error},
                    }
                    probe_attempt_records.append(technical_record)
                    _finish_attempt(entry, technical_record, "unresolved_technical")
                    break
                else:
                    selected_template = selected_candidate
            if unresolved_technical:
                break
            allowed = [selected_template] if selected_template else list(allowed_pool)
            prompt = _probe_prompt(payload, req, slice_, allowed, req_metadata, previous_note)
            selected_for_schema = selected_template
            if selected_for_schema:
                schema = pschema.probe_schema(selected_for_schema, rid)
                generator_seed = cr.derive_seed(
                    seed, TRACK, rid, req_index, "probe", attempt)
                (obj, parse_error, response, generator_technical_calls,
                 generator_reuse) = _attempt1_cached_call(
                    cache=attempt1_cache, stage="probe_generator", prompt=prompt,
                    response_schema=schema, model=model, role=ROLE_PROBE_GENERATOR,
                    seed=generator_seed, temperature=temperature,
                    output_token_limit=int(probe_num_predict),
                    provider_options={"ollama_num_ctx": ollama_num_ctx,
                                      "require_think_disabled": require_think_disabled},
                    stage_inputs={"problem_id": payload.get("problem_id"),
                                  "requirement_id": rid,
                                  "selected_template": selected_for_schema},
                    semantic_attempt=attempt + 1, candidate_id=candidate_id,
                    record_id=f"{rid}:attempt{attempt + 1}:probe_generator",
                    invoke=lambda: _call_json_with_technical_retries(
                        model, prompt, ledger, seed=generator_seed,
                        temperature=temperature, ollama_url=ollama_url,
                        max_tokens=int(probe_num_predict), num_ctx=ollama_num_ctx,
                        require_think_disabled=require_think_disabled,
                        response_schema=schema,
                        response_schema_name=f"track_b_probe_{selected_for_schema}",
                        accept=lambda value: (
                            "normalization_failed" if pe.normalize_probe(value, rid) is None else ""),
                        stage="probe_generator", problem_id=payload.get("problem_id"),
                        candidate_id=candidate_id, requirement_id=rid, attempt=attempt + 1,
                        stable_prefix=PROBE_GENERATOR_STABLE_PREFIX.format(
                            description=str(payload.get("problem_description", "")),
                            data=json.dumps(payload.get("data_instance", {}), ensure_ascii=False,
                                            separators=(",", ":")),
                            max_attempts=MAX_PROBE_ATTEMPTS),
                        role=ROLE_PROBE_GENERATOR,
                        context_safety_tokens=context_safety_tokens))
                reuse_records.append(generator_reuse)
                probes_generated += 1
            else:
                obj, parse_error, response, generator_technical_calls = (
                    None, "template_selector_failed", {"text": "",
                                                       "call_metadata": {}}, [])
                generator_reuse = {}
            if parse_error:
                unresolved_technical = True
                requirement_technical_failures += 1
            else:
                attempt_counts[rid] = attempt + 1
            attempt_record: Dict[str, Any] = {
                "requirement_id": rid, "attempt": attempt + 1,
                "semantic_attempt_consumed": not unresolved_technical,
                "technical_stage": "probe_generator" if unresolved_technical else "",
                "technical_calls": generator_technical_calls,
                "reuse": {"template_selector": (
                    selector_history[-1].get("reuse", {}) if selector_history else {}),
                          "probe_generator": generator_reuse},
                "template_selector": selector_history[-1] if selector_history else {},
                "selected_template": selected_template,
                "repair_feedback_for_generation": previous_note,
                "raw_generated_probe": obj,
                "raw_response": response.get("text", ""),
                "completion_status": response.get("completion_status", ""),
                "incomplete_reason": response.get("incomplete_reason", ""),
                "truncated": response.get("truncated", False),
                "normalized_probe": None,
                "typed_probe": None,
                "compiled_probe": None,
                "compiler_result": {"status": "NOT_RUN", "reason": "not_run"},
                "judge_visible_probe": None,
                "judge_visible_metadata": req_metadata,
                "judge_decisions": [],
                "judge_patches": [],
                "panel_action": "",
                "validator_result": {"ok": False, "reason": "not_run"},
                "execution_result": None,
                "execution_mode": "",
                "final_route": "generated",
            }
            probe_attempt_records.append(attempt_record)
            _checkpoint(attempt_record, "generated")
            if unresolved_technical:
                _finish_attempt(entry, attempt_record, "unresolved_technical")
                break

            # Judges 1 and 2 inspect the generated structured probe before deterministic
            # normalization and compilation. Both must ACCEPT; any REPAIR regenerates.
            first_two_record = _panel_gate(
                payload, req, obj, slice_, judge_panel, model, ledger, seed=seed,
                temperature=temperature, ollama_url=ollama_url,
                max_tokens=int(semantic_num_predict), phase="first_two",
                metadata=req_metadata, num_ctx=ollama_num_ctx,
                require_think_disabled=require_think_disabled,
                candidate_id=candidate_id, semantic_attempt=attempt + 1,
                attempt1_cache=attempt1_cache, reuse_records=reuse_records,
                context_safety_tokens=context_safety_tokens)
            _record_judge_stage(rid, attempt + 1, attempt_record,
                                first_two_record, "first_two")
            if first_two_record.get("requirement_unresolved"):
                unresolved_technical = True
                requirement_technical_failures += 1
                attempt_record["semantic_attempt_consumed"] = False
                attempt_record["technical_stage"] = first_two_record.get(
                    "technical_stage", "judges_1_2")
                attempt_record["panel_action"] = prt.ACTION_TECHNICAL_ERROR
                _finish_attempt(entry, attempt_record, "unresolved_technical")
                break
            if first_two_record.get("action") != prt.ACTION_EXECUTE:
                probes_unresolved += 1
                panel_repair_used[rid] = True
                attempt_record["panel_action"] = prt.ACTION_RECONSTRUCT
                previous_note = first_two_record.get("repair_note") or \
                    prt.semantic_repair_note(
                        "Judges 1–2 found a mathematical mismatch",
                        "the exact structured field identified by their repair",
                        ("all mathematical fields not identified by the repair",))
                _finish_attempt(entry, attempt_record, "judges_1_2_repair")
                continue

            generator_cache_key = str(generator_reuse.get("cache_key", ""))
            cached_generator = (
                attempt1_cache.get(generator_cache_key, {})
                if attempt1_cache is not None and generator_cache_key else {})
            if (generator_reuse.get("reused") and
                    isinstance(cached_generator.get("normalized_probe"), dict)):
                probe = copy.deepcopy(cached_generator["normalized_probe"])
                generator_reuse["reused_stages"] = list(dict.fromkeys([
                    *generator_reuse.get("reused_stages", []),
                    "raw_probe", "normalized_probe",
                ]))
            else:
                try:
                    probe = pe.normalize_probe(obj, rid) if obj is not None else None
                    if probe is not None:
                        probe = pe.canonicalize_probe(probe)   # deterministic canonical form
                        if (attempt1_cache is not None and attempt == 0 and
                                generator_cache_key in attempt1_cache):
                            attempt1_cache[generator_cache_key]["normalized_probe"] = (
                                copy.deepcopy(probe))
                except Exception as exc:
                    unresolved_technical = True
                    requirement_technical_failures += 1
                    attempt_record["technical_stage"] = "probe_normalization"
                    attempt_record["technical_reason"] = f"{type(exc).__name__}: {exc}"
                    _finish_attempt(entry, attempt_record, "unresolved_technical")
                    break
            attempt_record["typed_probe"] = copy.deepcopy(probe)
            try:
                compiled_probe, compiler_result = (
                    pe.compile_typed_probe(
                        probe, slice_, req_metadata,
                        problem_id=payload.get("problem_id"), allow_legacy=(model == "mock"))
                    if probe is not None else
                    (None, {"status": "NOT_PROBEABLE",
                            "reason": parse_error or "not_probeable:empty_response"})
                )
            except Exception as exc:
                unresolved_technical = True
                requirement_technical_failures += 1
                attempt_record["technical_stage"] = "probe_compilation"
                attempt_record["technical_reason"] = f"{type(exc).__name__}: {exc}"
                _finish_attempt(entry, attempt_record, "unresolved_technical")
                break
            attempt_record["compiler_result"] = compiler_result
            attempt_record["compiled_probe"] = copy.deepcopy(compiled_probe)
            if probe is not None and compiled_probe is None:
                reason = str(compiler_result.get("reason", "not_probeable:compiler_rejected"))
                previous_note = prt.semantic_repair_note(
                    reason, "parameters.contract",
                    ("all typed fields not identified by the compiler error",))
                if ("complete_big_m_linear_comparison_required" in reason and
                        "implication_probe" in remaining):
                    remaining.remove("implication_probe")
                    selected_template = None
                probes_unresolved += 1
                attempt_record["validator_result"] = {
                    "ok": False, "reason": reason, "stage": "typed_contract_compiler"}
                _finish_attempt(entry, attempt_record, "compiler_rejected")
                continue
            probe = compiled_probe
            attempt_record["normalized_probe"] = probe
            attempt_record["judge_visible_probe"] = probe
            conservation_check = (
                fsem.validate_conservation_probe(req, req_metadata, probe or {})
                if semantic_validation_mode != "off" else
                {"status": "OFF", "reason": "semantic validation disabled at runtime"})
            attempt_record["conservation_semantic_check"] = conservation_check
            if (semantic_validation_mode == "enforce" and
                    conservation_check.get("status") == "REPAIR"):
                previous_note = prt.semantic_repair_note(
                    str(conservation_check.get("reason", "conservation mismatch")),
                    "parameters.sense and the normalized equality terms",
                    ("the requirement scope, units, indices, and every already-correct term",))
                probes_unresolved += 1
                _finish_attempt(entry, attempt_record, "conservation_semantic_repair")
                continue

            # v41 configurable semantic gate.  Diagnostics are deliberately computed before the
            # judges.  In log-only mode this function is observational: the compiled probe object
            # is not mutated and proceeds to the panel unchanged.
            if semantic_validation_mode == "off":
                semantic_log_only = {
                    "mode": "off", "baseline_ok": None, "baseline_reason": "not_run",
                    "findings": {}, "would_reject_checks": [],
                }
            else:
                semantic_log_only = pe.semantic_validation_diagnostics(probe, slice_, req)
                semantic_log_only["findings"]["conservation_complete_balance"] = {
                    "would_reject": conservation_check.get("status") == "REPAIR",
                    "reason": str(conservation_check.get("reason", "ok")),
                }
                if conservation_check.get("status") == "REPAIR":
                    semantic_log_only["would_reject_checks"].append(
                        "conservation_complete_balance")
                semantic_log_only["mode"] = (
                    "log_only" if semantic_validation_mode == "log-only" else
                    "pre_enforcement_measurement")
            attempt_record["semantic_validator_log_only"] = semantic_log_only
            if semantic_validation_mode == "enforce":
                semantic_ok, semantic_reason = pe.validate_probe(
                    probe, slice_, req, semantic_checks=False,
                    equality_check=True, relevance_check=True,
                    zero_expression_guard=True, domain_property_check=True,
                    template_semantic_check=False)
                attempt_record["validator_result"] = {
                    "ok": bool(semantic_ok),
                    "reason": "ok" if semantic_ok else semantic_reason,
                    "mode": "enforce", "stage": "pre_judge_semantic_gate",
                    "enabled_checks": [
                        "equality_two_opposites", "relevance_grounding",
                        "zero_expression_guard", "domain_property_matching",
                        "conservation_complete_balance"],
                    "disabled_checks": ["template_requirement_matching"],
                }
                _checkpoint(attempt_record, "semantic_validated")
                if not semantic_ok:
                    probes_unresolved += 1
                    validation_errors.append(
                        f"{rid}:attempt{attempt + 1}:{semantic_reason}")
                    previous_note = prt.semantic_repair_note(
                        semantic_reason, semantic_reason.split(":", 1)[0],
                        ("all fields not identified by the validator error",))
                    _finish_attempt(entry, attempt_record, "semantic_validator_blocked")
                    continue

            # Generic validation checks the final normalized/compiled object before Judge 3.
            ok, reason = (pe.validate_probe(
                              probe, slice_, req, semantic_checks=False,
                              equality_check=False, relevance_check=False,
                              zero_expression_guard=False, domain_property_check=False,
                              template_semantic_check=False)
                          if probe is not None else (False, parse_error or "empty_response"))
            attempt_record.update({"normalized_probe": probe, "validation_ok": ok,
                                   "validation_error": "" if ok else reason})
            attempt_record["validator_result"] = {
                "ok": bool(ok), "reason": "ok" if ok else reason,
                "semantic_validation_mode": semantic_validation_mode,
                "semantic_checks_enforced": semantic_validation_mode == "enforce",
                "semantic_checks_log_only": semantic_validation_mode == "log-only",
            }
            _checkpoint(attempt_record, "validated")
            if unresolved_technical:
                break
            if not ok or probe is None or probe.get("probe_template") == "not_probeable":
                retried = retried or attempt < MAX_PROBE_ATTEMPTS - 1
                probes_unresolved += 1
                validation_errors.append(f"{rid}:attempt{attempt + 1}:{reason}")
                if probe is None and parse_error:
                    previous_note = prt.format_only_repair_note(parse_error)
                else:
                    previous_note = prt.semantic_repair_note(
                        reason, reason.split(":", 1)[0],
                        ("all fields not identified by the validator error",))
                if probe and probe.get("probe_template") in remaining:
                    remaining.remove(probe["probe_template"])
                    selected_template = None
                _finish_attempt(entry, attempt_record, "validator_blocked")
                continue

            probes_valid += 1
            if probe["probe_template"] in remaining:
                remaining.remove(probe["probe_template"])

            # Judge 3 sees the generated claim and the exact final normalized executable probe.
            # ACCEPT authorizes execution; REPAIR regenerates without executing this attempt.
            third_record = _panel_gate(
                payload, req, probe, slice_, judge_panel, model, ledger, seed=seed,
                temperature=temperature, ollama_url=ollama_url,
                max_tokens=int(semantic_num_predict), phase="judge3",
                claim=str((obj or {}).get("claim", "")), metadata=req_metadata,
                num_ctx=ollama_num_ctx,
                require_think_disabled=require_think_disabled,
                candidate_id=candidate_id, semantic_attempt=attempt + 1,
                attempt1_cache=attempt1_cache, reuse_records=reuse_records,
                context_safety_tokens=context_safety_tokens)
            _record_judge_stage(rid, attempt + 1, attempt_record,
                                third_record, "judge3")
            if third_record.get("requirement_unresolved"):
                unresolved_technical = True
                requirement_technical_failures += 1
                attempt_record["semantic_attempt_consumed"] = False
                attempt_record["technical_stage"] = third_record.get(
                    "technical_stage", "judge_3")
                attempt_record["panel_action"] = prt.ACTION_TECHNICAL_ERROR
                _finish_attempt(entry, attempt_record, "unresolved_technical")
                break
            if third_record.get("action") != prt.ACTION_EXECUTE:
                probes_unresolved += 1
                panel_repair_used[rid] = True
                attempt_record["panel_action"] = prt.ACTION_RECONSTRUCT
                previous_note = third_record.get("repair_note") or \
                    prt.semantic_repair_note(
                        "Judge 3 found claim/executable mathematical mismatch",
                        "the exact normalized executable field identified by the repair",
                        ("all mathematical fields not identified by the repair",))
                _finish_attempt(entry, attempt_record, "judge_3_repair")
                continue

            execution_mode = "verdict_bearing"
            attempt_record["execution_mode"] = execution_mode
            execution_modes[rid] = execution_mode
            attempt_record["panel_action"] = prt.ACTION_EXECUTE
            attempt_record["semantic_gate_status"] = "PANEL_CONFIRMED"
            attempt_record["semantic_alignment"] = {
                "semantic_alignment": "CONFIRMED",
                "requirement_id": rid,
                "reason": "selected three-judge panel authorized execution",
                "source": "selected_three_judge_panel",
            }

            try:
                result = pe.execute_probe(
                    probe, inventory, payload["candidate_code"], data, req_metadata,
                    cr.derive_seed(seed, TRACK, rid, req_index, "probe_execution"))
            except Exception as exc:
                unresolved_technical = True
                requirement_technical_failures += 1
                attempt_record["technical_stage"] = "probe_execution"
                attempt_record["technical_reason"] = f"{type(exc).__name__}: {exc}"
                attempt_record["panel_action"] = prt.ACTION_TECHNICAL_ERROR
                _finish_attempt(entry, attempt_record, "unresolved_technical")
                break
            solver_calls += int(result.get("solver_calls", 0) or 0)
            probes_executed += 1
            attempt_record["execution_result"] = result
            _checkpoint(attempt_record, "executed")
            status = result.get("status", "UNKNOWN")

            if status == "FAIL":
                label = "PROBE_FAIL"
            elif status == "PASS":
                label = "PROBE_PASS"
            else:
                probes_unresolved += 1
                previous_note = (str(result.get("warning") or result.get("message") or status) +
                                 ". This is warning/inconclusive only; choose a stronger template.")
                _finish_attempt(entry, attempt_record, "technical_execution_unresolved")
                continue

            _finish_attempt(entry, attempt_record, "verdict_bearing_execution")
            entry.update({"normalized_probe": probe, "execution_result": result,
                          "target_variables": probe.get("parameters", {}).get(
                              "target_variables", []),
                          "checked_property": probe.get("parameters", {}).get("property"),
                          "semantic_alignment": attempt_record.get("semantic_alignment"),
                          "structural_status": result.get("structural_status"),
                          "witness_status": result.get("witness_status"),
                          "result_label": label,
                          "status": "FAIL" if label == "PROBE_FAIL" else "PASS",
                          "decision_source": "probe_witness"})
            result_labels[rid] = label
            decision_sources[rid] = "probe_witness"
            decided = True
            break

        if not decided:
            label = _unresolved_requirement_label(unresolved_technical)
            source = (
                "unresolved_technical" if unresolved_technical else
                "unresolved_after_attempts")
            entry["result_label"] = label
            entry["status"] = label
            entry["decision_source"] = source
            entry["technical_failure"] = bool(unresolved_technical)
            result_labels[rid] = label
            decision_sources[rid] = source
            _reroute_latest(entry, source)
        probe_log.append(entry)
        if smoke_fail_fast and result_labels.get(rid) == "UNRESOLVED" and \
                bool(entry.get("technical_failure")):
            break

    # Isolated stage failures remain requirement-local UNRESOLVED results. A pervasive technical
    # collapse across at least 90% of a multi-requirement evaluation means the provider/runtime did
    # not permit meaningful candidate evaluation and is therefore a genuine system-level failure.
    if _systemic_requirement_failure(len(requirements), requirement_technical_failures):
        raise RuntimeError(
            "systemic_provider_or_runtime_failure: technical failure affected "
            f"{requirement_technical_failures}/{len(requirements)} requirements")

    # ----------------------- RETAINED PROBE-AWARE WITNESS FILTER ---------------------------
    deterministic_witness_ids = [
        rid for rid, label in result_labels.items()
        if label in {"PROBE_FAIL", "STRUCTURAL_FAIL"}
    ]
    fail_ids = list(deterministic_witness_ids)
    requirement_by_id = {str(item["requirement_id"]): item for item in requirements}
    entry_by_id = {str(item.get("requirement_id", "")): item for item in probe_log}
    authoritative_fail_ids = [
        rid for rid in fail_ids
        if se.is_authoritative_declared_attribute_failure(
            entry_by_id[rid].get("structural_evidence") or {})
    ]
    reviewable_fail_ids = [rid for rid in fail_ids if rid not in authoritative_fail_ids]

    verifier_retry_counts: Dict[Tuple[str, str], int] = {}

    def _verification_call(prompt: str, call_seed: Optional[int], max_tokens: int):
        if prompt.startswith("ROLE: Operations-research witness verifier"):
            stage = "witness_verifier_probe_aware_or"
            schema = pschema.witness_verifier_schema()
        elif prompt.startswith("ROLE: shadow root-cause adjudicator"):
            stage = "root_cause_adjudicator"
            schema = pschema.root_cause_schema(fail_ids)
        else:
            stage = "verification_unknown"
            schema = None
        retry_key = (stage, reqid.sha256_text(prompt))
        verifier_retry_counts[retry_key] = verifier_retry_counts.get(retry_key, 0) + 1
        try:
            return _call_json(
                model, prompt, ledger, seed=call_seed, temperature=temperature,
                ollama_url=ollama_url, max_tokens=max_tokens, num_ctx=ollama_num_ctx,
                require_think_disabled=require_think_disabled,
                response_schema=schema, response_schema_name=stage, stage=stage,
                problem_id=payload.get("problem_id"), candidate_id=candidate_id,
                attempt=1, technical_retry=verifier_retry_counts[retry_key], role=stage,
                stable_prefix=prompt.split("\n\n", 1)[0],
                context_safety_tokens=context_safety_tokens)
        except Exception as exc:
            return None, f"verification_technical_failure:{type(exc).__name__}:{exc}", {
                "text": "", "call_metadata": {
                    "stage": stage, "technical_failure": True,
                    "technical_reason": f"{type(exc).__name__}: {exc}"}}

    witness_verifier_b_records: Dict[str, Dict[str, Any]] = {}
    witness_verifier_skip_records = {
        rid: {"status": "SKIPPED", "result_label": label,
              "reason": f"witness verifier runs only for raw FAIL evidence; requirement ended as {label}"}
        for rid, label in result_labels.items() if rid not in fail_ids
    }
    authoritative_records: Dict[str, Dict[str, Any]] = {}
    for rid in authoritative_fail_ids:
        certificate = swa.build_witness_certificate(
            requirement_by_id[rid], fallback_metadata.get(rid, {}),
            entry_by_id[rid], inventory)
        authoritative_records[rid] = {
            "role": "deterministic_declared_attribute_certificate",
            "requirement_id": rid, "decision": swa.YES,
            "reason": "authoritative complete declared-attribute mismatch",
            "certificate": certificate, "evidence_tier": 1,
            "model_called": False, "model_call_count": 0,
            "witness_verifier_bypassed": True,
        }
        witness_verifier_skip_records[rid] = {
            "status": "SKIPPED_AUTHORITATIVE_DECLARED_ATTRIBUTE",
            "result_label": result_labels.get(rid),
            "reason": "complete metadata-scoped declared-attribute mismatch is authoritative",
            "evidence_tier": 1,
        }

    for rid in reviewable_fail_ids:
        def _rid_verification_call(prompt: str, call_seed: Optional[int],
                                   max_tokens: int, _rid=rid):
            obj, error, response = _verification_call(prompt, call_seed, max_tokens)
            metadata = response.get("call_metadata", {})
            if isinstance(metadata, dict):
                metadata["requirement_id"] = _rid
            return obj, error, response

        evidence_tier = int(tbl.classify_fail(entry_by_id[rid]).get("evidence_tier", 3))
        record = swa.verify_probe_aware(
            requirement_by_id[rid], fallback_metadata.get(rid, {}),
            entry_by_id[rid], inventory, call_json=_rid_verification_call, model=model,
            seed=cr.derive_seed(seed, TRACK, rid, "probe_aware_or_verifier"),
            max_tokens=int(witness_verifier_num_predict))
        record["evidence_tier"] = evidence_tier
        swa.assert_probe_aware_visible_contract(record)
        witness_verifier_b_records[rid] = record

    witness_technical_failures = sum(
        1 for record in witness_verifier_b_records.values()
        if record.get("status") == "UNRESOLVED" and
        bool(record.get("model_called")) and
        bool(record.get("technical_reason")))
    if _systemic_requirement_failure(
            len(requirements),
            requirement_technical_failures + witness_technical_failures):
        raise RuntimeError(
            "systemic_provider_or_runtime_failure: technical failure affected "
            f"{requirement_technical_failures + witness_technical_failures}/"
            f"{len(requirements)} requirements")

    official_fail_ids = [
        *authoritative_fail_ids,
        *[rid for rid in reviewable_fail_ids
          if witness_verifier_b_records[rid]["decision"] == swa.YES],
    ]
    official_result_labels = dict(result_labels)
    for rid in fail_ids:
        if rid in official_fail_ids:
            continue
        verifier_record = witness_verifier_b_records.get(rid) or {}
        if verifier_record.get("decision") == swa.NO:
            official_result_labels[rid] = swa.WITNESS_V_REJECT
            entry_by_id[rid]["official_decision_source"] = "witness_v_reject"
        else:
            official_result_labels[rid] = "UNRESOLVED"
            entry_by_id[rid]["official_decision_source"] = "witness_verifier_technical_unresolved"
    unresolved_ids = sorted(
        rid for rid, label in official_result_labels.items()
        if label in {"UNRESOLVED", swa.WITNESS_V_REJECT})
    evaluation_complete = (
        len(official_result_labels) == len(requirements) and not unresolved_ids)
    for rid, label in official_result_labels.items():
        if rid in entry_by_id:
            entry_by_id[rid]["official_result_label"] = label

    localization = tbl.localize(probe_log, official_result_labels)
    evidence_tiers = {
        str(item.get("requirement_id", "")): int(item.get("evidence_tier", 5) or 5)
        for item in localization.get("localization_evidence", [])
        if str(item.get("requirement_id", "")) in official_fail_ids
    }
    confirmed_records = [
        authoritative_records[rid] if rid in authoritative_records
        else witness_verifier_b_records[rid]
        for rid in official_fail_ids
    ]
    root_record = swa.adjudicate_root_cause(
        requirements, confirmed_records, call_json=_verification_call, model=model,
        seed=cr.derive_seed(seed, TRACK, "shadow_root_cause", "|".join(official_fail_ids)),
        max_tokens=int(root_cause_num_predict),
        deterministic_fallback_ranking=localization.get("ranked_requirement_ids", []),
        evidence_tiers=evidence_tiers)
    root_primary = (
        root_record.get("primary_requirement_id")
        if root_record.get("decision") == swa.RANKED else None)
    root_ranked_ids = root_record.get("ranked_requirement_ids", [])

    if attempt_record_path:
        try:
            attempt_path = Path(attempt_record_path)
            pfor.write_problem_report(
                output_dir=attempt_path.parent.parent,
                problem_id=payload.get("problem_id", "unknown"),
                run_key=attempt_path.stem, candidate_id=str(candidate_id or "unknown"),
                requirements=requirements, attempts=probe_attempt_records,
                probe_aware_records=witness_verifier_b_records,
                root_cause_record=root_record)
        except Exception as exc:
            validation_errors.append(
                f"probe_forensics_write_failed:{type(exc).__name__}:{exc}")

    # Confirmed failures determine INCORRECT; otherwise the public verdict is CORRECT.
    # evaluation_complete separately records whether every requirement was resolved. Genuine
    # system-level exceptions are converted to PIPELINE_ERROR by run_exp2.py.
    verdict = _aggregate_candidate_verdict(official_fail_ids)
    verdict_source = (
        "PROBE_AWARE_WITNESS_VERIFIER" if official_fail_ids else
        "NO_CONFIRMED_FAILURE")

    categories: List[str] = []
    reasons: List[str] = []
    evidence: Dict[str, Any] = {}
    for entry in probe_log:
        rid = entry["requirement_id"]
        label = entry.get("result_label")
        evidence[rid] = {"result_label": label,
                         "decision_source": entry.get("decision_source"),
                         "normalized_probe": entry.get("normalized_probe"),
                         "target_variables": entry.get("target_variables", []),
                         "checked_property": entry.get("checked_property"),
                         "semantic_alignment": entry.get("semantic_alignment"),
                         "structural_status": entry.get("structural_status"),
                         "witness_status": entry.get("witness_status"),
                         "structural_evidence": entry.get("structural_evidence"),
                         "probe_aware_witness_verifier":
                             witness_verifier_b_records.get(rid)}
        if rid in official_fail_ids and label == "PROBE_FAIL":
            probe = entry.get("normalized_probe") or {}
            result = entry.get("execution_result") or entry.get("tier1") or {}
            categories.append(result.get("taxonomy") or pe.taxonomy_for_failure(
                requirement=next(r for r in requirements if r["requirement_id"] == rid),
                probe=probe, result=result))
            reasons.append(f"{rid}: {result.get('structural_detail') or result.get('message') or 'confirmed violation'}")
        elif rid in official_fail_ids and label == "STRUCTURAL_FAIL":
            structural = entry.get("structural_evidence") or {}
            categories.append(structural.get("taxonomy", "domain_or_bound_error"))
            reasons.append(f"{rid}: {structural.get('reason', 'strong structural mismatch')}")

    taxonomy = (
        categories[0] if categories and len(set(categories)) == 1 else
        "mixed_or_unclear" if categories else "none")
    pred = {
        "verdict": verdict,
        "suspected_requirement_ids": official_fail_ids,
        "primary_suspected_requirement_id": (
            (root_primary or localization["primary_suspected_requirement_id"])
            if official_fail_ids
            else None),
        "predicted_taxonomy_category": taxonomy if verdict == "incorrect" else "none",
        "error_reason": ("; ".join(reasons) if verdict == "incorrect" else ""),
        "evidence": evidence if verdict == "incorrect" else "",
        "confidence": (
            1.0 if any(result_labels.get(rid) == "PROBE_FAIL" for rid in official_fail_ids)
            else 0.9 if official_fail_ids
            else 0.9),
    }
    prediction_valid, prediction_errors = rp.validate_prediction(
        pred, [r["requirement_id"] for r in payload["requirements"]],
        parse_ok=True, executed_fail_ids=official_fail_ids,
        allow_unlocalized_incorrect=False)
    for entry in probe_log:
        rid = str(entry.get("requirement_id", ""))
        requirement_summaries.append({
            "requirement_id": rid,
            "structural": {
                "cached": True,
                "status": (entry.get("structural_evidence") or {}).get("status"),
                "sufficient": (entry.get("structural_evidence") or {}).get("sufficient"),
                "coverage": (entry.get("structural_evidence") or {}).get("coverage"),
                "requirement_complete_pass": (
                    entry.get("structural_evidence") or {}).get(
                        "requirement_complete_pass", False),
                "reason": (entry.get("structural_evidence") or {}).get("reason"),
            },
            "attempts": [
                {
                    "attempt": record.get("attempt"),
                    "template": (record.get("normalized_probe") or {}).get("probe_template"),
                    "votes": ((record.get("judge_panel") or {}).get("verdicts") or []),
                    "panel_action": record.get("panel_action"),
                    "validator": record.get("validator_result"),
                    "execution_mode": record.get("execution_mode"),
                    "execution_status": (record.get("execution_result") or {}).get("status"),
                    "route": record.get("final_route"),
                }
                for record in entry.get("attempts", [])
            ],
            "probe_aware_witness_verifier": witness_verifier_b_records.get(rid),
            "witness_verifier_skip": witness_verifier_skip_records.get(rid),
            "final_status": entry.get("official_result_label", entry.get("status")),
            "result_label": entry.get("official_result_label", entry.get("result_label")),
            "raw_result_label": entry.get("result_label"),
            "decision_source": entry.get("decision_source"),
        })

    return pred, {
        "architecture": swa.ARCHITECTURE_NAME,
        "track_b_configuration": "v42_probe_aware_root",
        "evidence_hierarchy": (
            "tier1:complete_metadata_scoped_declared_attribute_fail_no_witness; "
            "tier2:other_structural_fail_with_witness; "
            "tier3:executable_fail_with_witness; tier4:partial_or_unresolved; "
            "tier5:llm_only; root ranking must preserve tier order"),
        "judge_panel_version": judge_panel or "",
        "judge_panel_records": panel_records,
        "back_translations_executed": 0,
        "back_translations_skipped": 0,
        "judge_3_calls_executed": sum(
            int(record.get("phase") == "judge3") for record in panel_records),
        "judge_3_calls_skipped": sum(
            int(any(stage.get("phase") == "first_two"
                    for stage in record.get("judge_stages", [])) and
                not any(stage.get("phase") == "judge3"
                        for stage in record.get("judge_stages", [])))
            for record in probe_attempt_records),
        "panel_decision": panel_decisions,
        "execution_modes": execution_modes,
        "attempt_counts": attempt_counts,
        "diagnostic_only_ids": sorted(r for r, m in execution_modes.items()
                                      if m == "diagnostic_only"),
        "diagnostic_fail_requirement_ids": sorted({
            str(record.get("requirement_id", ""))
            for record in probe_attempt_records
            if record.get("execution_mode") == "diagnostic_only"
            and (record.get("execution_result") or {}).get("status") == "FAIL"
        }),
        "judge_audit": panel_judge_log,
        "judge_panel_actions": panel_actions,
        "judge_panel_executed": sum(1 for a in panel_actions.values()
                                    if a == prt.ACTION_EXECUTE),
        "judge_panel_repaired": sum(1 for v in panel_repair_used.values() if v),
        "judge_panel_leak_violations": panel_leak_violations,
        "semantic_validation_mode": semantic_validation_mode,
        "semantic_would_reject_count": sum(
            len((record.get("semantic_validator_log_only") or {}).get(
                "would_reject_checks", [])) for record in probe_attempt_records),
        "semantic_would_reject_by_check": {
            check: sum(
                int(check in ((record.get("semantic_validator_log_only") or {}).get(
                    "would_reject_checks", []))) for record in probe_attempt_records)
            for check in (
                "equality_two_opposites", "relevance_grounding",
                "zero_expression_guard", "domain_property_matching",
                "conservation_complete_balance", "template_requirement_matching")
        },
        "verdict_source": verdict_source,
        "deterministic_witness_ids": deterministic_witness_ids,
        "deterministic_witness_count": len(deterministic_witness_ids),
        "probe_attempt_records": probe_attempt_records,
        "attempt1_reuse_records": reuse_records,
        "attempt1_artifacts_generated_normally": sum(
            int(not record.get("reused", False)) for record in reuse_records),
        "attempt1_artifacts_reused": sum(
            int(record.get("reused", False)) for record in reuse_records),
        "calls_saved_through_reuse": sum(
            int(record.get("reused", False)) for record in reuse_records),
        "requirement_scope_ids": [str(item["requirement_id"]) for item in requirements],
        "requirements_skipped_by_scope": [
            rid for rid in all_requirement_ids
            if rid not in {str(item["requirement_id"]) for item in requirements}],
        "deterministic_evidence_records": deterministic_evidence_records,
        "unresolved_requirement_ids": unresolved_ids,
        "requirement_summaries": requirement_summaries,
        "executed_probes": probes_executed,
        "total_requirements": len(requirements),
        "input_tokens": ledger.input_tokens, "output_tokens": ledger.output_tokens,
        "total_tokens": ledger.input_tokens + ledger.output_tokens,
        "runtime_sec": round(ledger.runtime, 3), "solver_calls": solver_calls,
        "truncated": any(c.get("truncated", False) for c in ledger.calls),
        "parse_ok": True, "prediction_valid": prediction_valid,
        "validation_errors": "; ".join(validation_errors + prediction_errors),
        "retried": retried, "error": "",
        "raw_responses": ledger.raws, "call_metadata": ledger.calls,
        "probes_generated": probes_generated, "probes_valid": probes_valid,
        "probes_unknown": probes_unresolved, "probes_executed": probes_executed,
        "executed_fail_count": sum(
            label in {"PROBE_FAIL", "STRUCTURAL_FAIL"}
            for label in result_labels.values()),
        "executed_fail_requirement_ids": [rid for rid, label in result_labels.items()
                                          if label in {"PROBE_FAIL", "STRUCTURAL_FAIL"}],
        "probe_result_adherence": "", "probe_verdict_conflict": False,
        "probe_log": probe_log, "requirement_result_labels": result_labels,
        "primary_suspected_requirement_id":
            localization["primary_suspected_requirement_id"],
        "root_cause_requirement_ids": localization["root_cause_requirement_ids"],
        "collateral_requirement_ids": localization["collateral_requirement_ids"],
        "localization_evidence": localization["localization_evidence"],
        "decision_sources": decision_sources, "fallback_count": fallback_count,
        "pipeline_error_count": 0,
        "unresolved_requirement_count": len(unresolved_ids),
        "evaluation_complete": evaluation_complete,
        "semantic_confirmation_calls": semantic_calls, "llm_final_verdict": "",
        # --- v20 semantic reconstruction gate accounting ---
        "semantic_gate": "selected_three_judge_panel",
        "semantic_agent_pipeline_errors": 0,
        "semantic_attempt_records": [],
        "semantic_attempts_total": 0,
        "semantic_match_count": 0,
        "semantic_mismatch_count": 0,
        "semantic_pipeline_error_count": 0,
        "semantic_exhausted_requirement_ids": [],
        "enforced_final_verdict": verdict,
        "probe_coverage": cr.resolved_probe_coverage(result_labels, len(requirements)),
        "initial_verdict": "", "decision_mode": "systematic_requirement_probing",
        "probe_attempted": bool(probes_generated),
        "probe_execution_rate": min(1.0, probes_executed / max(1, probes_generated)),
        # The probe-aware verifier is the sole witness policy in the retained V42 pipeline.
        "raw_fail_requirement_ids": fail_ids,
        "authoritative_declared_attribute_fail_requirement_ids": authoritative_fail_ids,
        "authoritative_declared_attribute_fail_count": len(authoritative_fail_ids),
        "witness_reviewable_fail_requirement_ids": reviewable_fail_ids,
        "official_retained_fail_requirement_ids": official_fail_ids,
        "official_witness_policy": "probe_aware_root",
        "official_requirement_result_labels": official_result_labels,
        "current_ranked_requirement_ids": localization.get(
            "ranked_requirement_ids", []),
        "witness_probe_aware_records": witness_verifier_b_records,
        "witness_verifier_skip_records": witness_verifier_skip_records,
        "witness_verifier_calls_executed": len(witness_verifier_b_records),
        "witness_verifier_calls_skipped": len(witness_verifier_skip_records),
        "witness_probe_aware_call_count": sum(
            int(record.get("model_call_count", int(record.get("model_called", False))))
            for record in witness_verifier_b_records.values()),
        "root_cause_record": root_record,
        "root_cause_call_count": int(root_record.get(
            "model_call_count", int(root_record.get("model_called", False)))),
        "root_cause_calls_executed": int(root_record.get("model_called", False)),
        "root_cause_calls_skipped": int(not root_record.get("model_called", False)),
        "root_primary_requirement_id": root_primary,
        "root_ranked_requirement_ids": root_ranked_ids,
        "inference_stage_failure_counts": {
            stage: {
                "calls": sum(
                    1 for item in ledger.calls
                    if item.get("pipeline_stage") == stage),
                "empty": sum(
                    1 for item in ledger.calls
                    if item.get("pipeline_stage") == stage
                    and item.get("empty_response")),
                "truncated": sum(
                    1 for item in ledger.calls
                    if item.get("pipeline_stage") == stage
                    and item.get("truncated")),
                "think_fallback": sum(
                    1 for item in ledger.calls
                    if item.get("pipeline_stage") == stage
                    and item.get("think_fallback_used")),
            }
            for stage in sorted({
                str(item.get("pipeline_stage", "unknown"))
                for item in ledger.calls})
        },
    }
