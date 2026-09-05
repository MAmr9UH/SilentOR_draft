#!/usr/bin/env python3
"""
common_runner.py -- shared model-call infrastructure for retained V42.

Provides:
  - call_model(): dispatches to the tested OpenAI / Ollama callers in llm_clients.py, with
    provider inferred from model name; returns text + token counts + timing.
  - extract_json(): robustly pulls a JSON object from an LLM response (handles fences, prose).
"""
from __future__ import annotations
import csv, hashlib, importlib.util, json, os, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
_llm = importlib.util.spec_from_file_location("llm_clients", HERE / "llm_clients.py")
llm = importlib.util.module_from_spec(_llm); _llm.loader.exec_module(llm)

# Complete attempt records can legitimately make one CSV field much larger than Python's default
# 128 KiB parser limit. Use the largest platform-supported limit for resume/scoring compatibility.
_csv_limit = sys.maxsize
while True:
    try:
        csv.field_size_limit(_csv_limit)
        break
    except OverflowError:
        _csv_limit //= 10

OPENAI_MODELS_PREFIXES = ("gpt-", "o1", "o3", "o4")


def infer_provider(model: str) -> str:
    """Map a model string to its backend provider adapter.

    V42 calls models exclusively through call_model(), so the verifier is model-agnostic:
    attaching a new verifier (GPT, Gemma, Llama, SIRL, or any other) is purely a matter of routing its model string here.  OpenAI
    models are matched by prefix; everything else is served through the local Ollama adapter
    (Gemma/Llama/SIRL and other open weights).  To add a distinct hosted backend, add a
    prefix branch here and a corresponding llm_clients.call_<provider> function -- no track,
    contract, probe, or reporting code changes.
    """
    m = model.lower()
    if any(m.startswith(p) for p in OPENAI_MODELS_PREFIXES):
        return "openai"
    return "ollama"


def derive_seed(base_seed, *parts):
    """Stable distinct seed derived from a run seed and call-specific labels."""
    if base_seed is None:
        return None
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return (int(base_seed) + int.from_bytes(digest[:4], "big")) % 2_147_483_647


def canonical_json(value) -> str:
    """Return a deterministic representation for arbitrary JSON-like model output.

    LLMs occasionally put objects or arrays where the schema expects scalar identifiers.  Such
    values must still be rejected by validation, but they must never crash deduplication or set
    membership with ``TypeError: unhashable type: 'dict'``.
    """
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                          default=str)
    except (TypeError, ValueError):
        return repr(value)


def canonical_key(value) -> str:
    """Hash/set-safe key that preserves the JSON type as well as its content."""
    return f"{type(value).__name__}:{canonical_json(value)}"


def stable_unique(values):
    """Deduplicate possibly nested JSON values without requiring them to be hashable."""
    seen = set()
    result = []
    for value in values or []:
        key = canonical_key(value)
        if key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def resolved_probe_coverage(requirement_result_labels, total_requirements) -> float:
    """Unique deterministic PASS/FAIL requirements divided by the visible requirement count."""
    try:
        total = max(0, int(total_requirements))
    except (TypeError, ValueError):
        total = 0
    if total == 0 or not isinstance(requirement_result_labels, dict):
        return 0.0
    resolved = {
        str(requirement_id)
        for requirement_id, label in requirement_result_labels.items()
        if label in (
            "PROBE_PASS", "PROBE_FAIL",
            "STRUCTURAL_PASS", "STRUCTURAL_PASS_LAST_RESORT", "STRUCTURAL_FAIL",
        )
    }
    return min(1.0, max(0.0, len(resolved) / total))


def call_model(model, prompt, *, temperature=None, seed=None, num_predict=4000,
               request_timeout=600, ollama_url="http://localhost:11434/api/generate",
               api_retries=2, retry_truncation=True, truncation_retry_cap=16000,
               response_schema=None, response_schema_name=None,
               num_ctx=None, require_think_disabled=False, call_context=None):
    """Unified call. Returns dict: text, input_tokens, output_tokens, total_tokens,
    runtime_sec, provider, truncated.

    A response that ends specifically because of the output-token limit is retried once with a
    larger, preregistered allowance.  This is an infrastructure recovery, not a label-dependent
    retry: the same rule applies to every model, track, candidate, and verdict.  Token/runtime
    accounting includes both attempts, while ``truncated`` describes the final attempt and
    ``truncation_recovered`` records a successful recovery.
    """
    provider = infer_provider(model)
    t0 = time.time()
    attempt_records = []
    total_input = total_output = 0
    current_limit = max(1, int(num_predict))
    final_r = None
    final_status = ""
    final_reason = ""
    final_truncated = False

    def invoke(limit):
        for api_attempt in range(api_retries + 1):
            try:
                if provider == "openai":
                    if response_schema is None:
                        response = llm.call_openai(
                            model, prompt, temperature, seed, request_timeout, limit)
                    else:
                        response = llm.call_openai(
                            model, prompt, temperature, seed, request_timeout, limit,
                            response_schema=response_schema,
                            schema_name=response_schema_name)
                else:
                    if response_schema is None:
                        response = llm.call_ollama(
                            model, prompt, ollama_url, temperature, seed, request_timeout, limit,
                            num_ctx=num_ctx,
                            require_think_disabled=require_think_disabled)
                    else:
                        response = llm.call_ollama(
                            model, prompt, ollama_url, temperature, seed, request_timeout, limit,
                            response_schema=response_schema,
                            schema_name=response_schema_name, num_ctx=num_ctx,
                            require_think_disabled=require_think_disabled)
                return response, api_attempt + 1
            except Exception:
                if api_attempt >= api_retries:
                    raise
                time.sleep(min(2 ** api_attempt, 4))

    for truncation_attempt in range(2):
        r, api_attempts_used = invoke(current_limit)
        if provider == "openai":
            status = str(r.get("openai_status", "") or "")
            incomplete_reason = str(r.get("openai_incomplete_reason", "") or "")
            truncated = incomplete_reason == "max_output_tokens"
        else:
            status = "completed" if r.get("done", True) else "incomplete"
            incomplete_reason = ("" if r.get("done", True)
                                 else str(r.get("done_reason", "incomplete")))
            truncated = (str(r.get("done_reason", "")) == "length" or
                         int(r.get("eval_count", 0) or 0) >= current_limit)
        input_tokens = int(r.get("prompt_eval_count", 0) or 0)
        output_tokens = int(r.get("eval_count", 0) or 0)
        total_input += input_tokens
        total_output += output_tokens
        attempt_records.append({
            "attempt": truncation_attempt + 1,
            "requested_output_token_limit": current_limit,
            "effective_output_token_limit": r.get(
                "effective_output_token_limit", current_limit),
            "completion_status": status,
            "incomplete_reason": incomplete_reason,
            "truncated": truncated,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": r.get("openai_reasoning_tokens", ""),
            "api_attempts": api_attempts_used,
            "prompt_eval_count": input_tokens,
            "eval_count": output_tokens,
            "done": r.get("done", status == "completed"),
            "done_reason": r.get("done_reason", incomplete_reason),
            "requested_num_ctx": num_ctx,
            "effective_num_ctx": r.get("effective_num_ctx"),
            "think_requested": r.get("think_requested", False),
            "think_honored": r.get("think_honored", True),
            "think_fallback_used": r.get("think_fallback_used", False),
            "think_fallback_http_status": r.get("think_fallback_http_status"),
        })
        final_r, final_status, final_reason, final_truncated = (
            r, status, incomplete_reason, truncated)
        if not truncated or not retry_truncation or truncation_attempt == 1:
            break
        next_limit = min(int(truncation_retry_cap), current_limit * 2)
        if next_limit <= current_limit:
            break
        current_limit = next_limit

    runtime = time.time() - t0
    effective_limit = final_r.get("effective_output_token_limit", current_limit)
    recovered = len(attempt_records) > 1 and attempt_records[0]["truncated"] and not final_truncated
    reported_cached = final_r.get("cached_input_tokens", "")
    cached_available = reported_cached not in (None, "")
    cached_input_tokens = int(reported_cached or 0) if cached_available else ""
    final_input_tokens = int(final_r.get("prompt_eval_count", 0) or 0)
    uncached_input_tokens = (
        max(0, final_input_tokens - int(cached_input_tokens)) if cached_available else "")
    context = dict(call_context or {})
    stable_prefix = context.pop("stable_prefix", "")
    stable_prefix_hash = (
        hashlib.sha256(str(stable_prefix).encode("utf-8")).hexdigest()
        if stable_prefix not in (None, "") else "")
    schema_hash = (
        hashlib.sha256(canonical_json(response_schema).encode("utf-8")).hexdigest()
        if response_schema is not None else "")
    metadata = {
        "provider": provider,
        "model": model,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_character_count": len(prompt),
        "prompt_utf8_bytes": len(prompt.encode("utf-8")),
        "requested_seed": seed,
        "effective_seed": r.get("effective_seed", seed),
        "requested_temperature": temperature,
        "effective_temperature": r.get("effective_temperature", temperature),
        "requested_output_token_limit": num_predict,
        "effective_output_token_limit": effective_limit,
        "completion_status": final_status,
        "incomplete_reason": final_reason,
        "truncated": final_truncated,
        "had_truncation": any(item["truncated"] for item in attempt_records),
        "truncation_retry_count": max(0, len(attempt_records) - 1),
        "truncation_recovered": recovered,
        "attempts": attempt_records,
        "dropped_parameters": final_r.get("dropped_parameters", []),
        "reasoning_tokens": final_r.get("openai_reasoning_tokens", ""),
        "input_tokens": final_input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "uncached_input_tokens": uncached_input_tokens,
        "output_tokens": int(final_r.get("eval_count", 0) or 0),
        "provider_cache_status": (
            "reported_hit" if cached_available and int(cached_input_tokens) > 0 else
            "reported_miss" if cached_available else "unavailable"),
        "api_attempts": sum(item["api_attempts"] for item in attempt_records),
        "structured_output_requested": response_schema is not None,
        "structured_output_enforced": bool(final_r.get("structured_output_enforced", False)),
        "structured_output_schema_name": response_schema_name or "",
        "structured_output_schema_sha256": schema_hash,
        "response_schema_hash": schema_hash,
        "stable_prefix_hash": stable_prefix_hash,
        "prompt_eval_count": int(final_r.get("prompt_eval_count", 0) or 0),
        "eval_count": int(final_r.get("eval_count", 0) or 0),
        "done": final_r.get("done", final_status == "completed"),
        "done_reason": final_r.get("done_reason", final_reason),
        "requested_num_ctx": num_ctx,
        "effective_num_ctx": final_r.get("effective_num_ctx"),
        "num_ctx_explicit": bool(final_r.get("num_ctx_explicit", False)),
        "think_requested": bool(final_r.get("think_requested", False)),
        "think_honored": bool(final_r.get("think_honored", True)),
        "think_fallback_used": bool(final_r.get("think_fallback_used", False)),
        "think_fallback_http_status": final_r.get("think_fallback_http_status"),
        "empty_response": not bool(str(final_r.get("response", "") or "").strip()),
        **context,
    }
    return {"text": final_r.get("response", "") or "",
            "input_tokens": total_input, "output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "runtime_sec": round(runtime, 3), "provider": provider,
            "truncated": final_truncated, "had_truncation": metadata["had_truncation"],
            "truncation_recovered": recovered,
            "completion_status": final_status, "incomplete_reason": final_reason,
            "call_metadata": metadata}


def extract_json(text: str):
    """Pull the first well-formed JSON object from a model response. Handles ```json fences,
    leading prose, and trailing prose. Returns (obj_or_None, error_or_None)."""
    if not text:
        return None, "empty response"
    # strip code fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates = []
    if fenced:
        candidates.append(fenced.group(1))
    # greedy first {...last }
    b0, b1 = text.find("{"), text.rfind("}")
    if b0 != -1 and b1 != -1 and b1 > b0:
        candidates.append(text[b0:b1 + 1])
    # brace-matched scan from first {
    if b0 != -1:
        depth = 0
        for i in range(b0, len(text)):
            if text[i] == "{": depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidates.append(text[b0:i + 1]); break
    for c in candidates:
        try:
            return json.loads(c), None
        except json.JSONDecodeError:
            continue
    return None, "no parseable JSON object found"
