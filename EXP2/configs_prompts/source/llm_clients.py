"""Shared OpenAI Responses API and Ollama model-calling logic for Exp 2.

The Responses API does not accept ``seed``.  Exp 2 still records every requested
repetition seed for provenance, but never sends that unsupported field to OpenAI.
Ollama continues to receive its supported ``seed`` option.
"""
from __future__ import annotations
import json, os, re, urllib.request, urllib.error

def _usage_value(usage, *names):
    if usage is None:
        return ""
    for name in names:
        if isinstance(usage, dict) and name in usage:
            return usage.get(name, "")
        value = getattr(usage, name, "")
        if value != "":
            return value
    return ""

def call_ollama(model, prompt, ollama_url, temperature, seed, request_timeout, num_predict,
                disable_think=True, response_schema=None, schema_name=None,
                num_ctx=None, require_think_disabled=False):
    options = {"num_predict": num_predict}
    if num_ctx is not None:
        options["num_ctx"] = int(num_ctx)
    if temperature is not None:
        options["temperature"] = temperature
    if seed is not None:
        options["seed"] = seed
    payload = {"model": model, "prompt": prompt, "stream": False, "options": options}
    if response_schema is not None:
        # Ollama accepts a JSON Schema object in ``format``.  This prevents local verifier
        # models from replacing official requirement IDs with candidate variable/row names.
        payload["format"] = response_schema
    if disable_think:
        # Thinking models (for example, deepseek-r1) can use most of num_predict on <think> blocks,
        # truncating the actual code ("missing solve", unterminated strings). Ollama >= 0.9
        # honors think=false; older servers may reject the field, so fall back gracefully.
        payload["think"] = False
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(ollama_url, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=request_timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            result["effective_temperature"] = temperature
            result["effective_seed"] = seed
            result["dropped_parameters"] = []
            result["structured_output_enforced"] = response_schema is not None
            result["structured_output_schema_name"] = schema_name or ""
            result["requested_num_ctx"] = num_ctx
            # Ollama accepts ``num_ctx`` as a per-request runtime option. A successful request
            # with the option present is the strongest per-call acknowledgement available in
            # the non-streaming generate response; the separate preflight verifies it against
            # the model's advertised maximum before evaluated calls begin.
            result["effective_num_ctx"] = int(num_ctx) if num_ctx is not None else None
            result["num_ctx_explicit"] = num_ctx is not None
            result["think_requested"] = bool(disable_think)
            thinking_text = str(result.get("thinking", "") or "")
            visible_text = str(result.get("response", "") or "")
            result["think_honored"] = bool(
                disable_think and not thinking_text.strip() and
                not visible_text.lstrip().startswith("<think>"))
            result["think_fallback_used"] = False
            result["think_fallback_http_status"] = None
            if disable_think and require_think_disabled and not result["think_honored"]:
                raise RuntimeError(
                    "Ollama returned thinking content despite think=false; refusing "
                    "to continue the evaluated call")
            return result
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = ""
        think_rejected = "think" in error_body.lower()
        if disable_think and e.code in (400, 422) and think_rejected:
            if require_think_disabled:
                raise RuntimeError(
                    f"Ollama rejected think=false with HTTP {e.code}; "
                    f"refusing a silent thinking-mode fallback: {error_body[:500]}") from e
            result = call_ollama(
                model, prompt, ollama_url, temperature, seed, request_timeout,
                num_predict, disable_think=False,
                response_schema=response_schema, schema_name=schema_name,
                num_ctx=num_ctx, require_think_disabled=False)
            result["think_requested"] = True
            result["think_honored"] = False
            result["think_fallback_used"] = True
            result["think_fallback_http_status"] = int(e.code)
            return result
        raise

def call_openai(model, prompt, temperature, seed, request_timeout, num_predict,
                response_schema=None, schema_name=None):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment")
    try:
        from openai import OpenAI
        from openai import BadRequestError
    except ImportError as e:
        raise RuntimeError("OpenAI Python SDK is not installed. Run: pip install openai") from e
    client = OpenAI(api_key=api_key, timeout=request_timeout)
    request = {
        "model": model,
        "input": prompt,
        "max_output_tokens": num_predict,
        "reasoning": {"effort": "minimal"},
    }
    if temperature is not None:
        request["temperature"] = temperature
    if response_schema is not None:
        safe_name = re.sub(r"[^A-Za-z0-9_-]", "_", schema_name or "exp2_structured")[:64]
        request["text"] = {"format": {
            "type": "json_schema", "name": safe_name or "exp2_structured",
            "strict": True, "schema": response_schema,
        }}

    # The Responses API has no `seed` request field.  Preserve the requested seed in the
    # experiment log (common_runner does this), and record it here as deliberately dropped.
    # This must be done before calling the SDK: unsupported SDK keyword arguments raise a
    # local TypeError, not an API BadRequestError, so the API fallback below cannot catch them.
    dropped_parameters = ["seed"] if seed is not None else []

    # Reasoning models (gpt-5-nano, o-series, ...) may reject optional sampling params such as
    # `temperature` (only the default temperature=1 is allowed). Rather than
    # hard-code which model rejects which field, we send the params and, if the API responds
    # with "Unsupported parameter: '<name>'", drop that field and retry. This mirrors the
    # Ollama `think=false` fallback and keeps a single code path for all providers.
    # It does NOT change temperature for models that accept it.
    _optional = ("temperature", "max_output_tokens")
    while True:
        try:
            response = client.responses.create(**request)
            break
        except BadRequestError as e:
            msg = str(getattr(e, "message", "") or e)
            dropped = None
            for name in _optional:
                # match the API's "Unsupported parameter: 'temperature'" / "not supported"
                if name in request and name in msg and (
                        "unsupported" in msg.lower() or "not supported" in msg.lower()
                        or "unknown" in msg.lower()):
                    request.pop(name, None)
                    dropped = name
                    break
            if dropped is None:
                raise
            dropped_parameters.append(dropped)
            # loop and retry without the offending field
    raw_text = getattr(response, "output_text", None)
    if raw_text is None:
        parts = []
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                text_part = getattr(content, "text", None)
                if text_part is not None:
                    parts.append(text_part)
        raw_text = "\n".join(parts)
    usage = getattr(response, "usage", None)
    # Reasoning models (gpt-5-nano, o-series) share max_output_tokens between hidden
    # reasoning and visible output. When reasoning consumes the budget, the API returns
    # status="incomplete" (reason="max_output_tokens") with an empty/partial output_text.
    # Surface that here so the run row can flag truncation instead of misreading a
    # token-starved response as "model produced no code". Diagnostic only; no label logic.
    status = getattr(response, "status", None)
    incomplete = getattr(response, "incomplete_details", None)
    incomplete_reason = getattr(incomplete, "reason", None) if incomplete else None
    reasoning_tokens = ""
    cached_input_tokens = ""
    try:
        details = getattr(usage, "output_tokens_details", None)
        reasoning_tokens = _usage_value(details, "reasoning_tokens")
        input_details = getattr(usage, "input_tokens_details", None)
        cached_input_tokens = _usage_value(input_details, "cached_tokens")
    except Exception:
        pass
    return {
        "response": raw_text or "",
        "prompt_eval_count": _usage_value(usage, "input_tokens", "prompt_tokens"),
        "eval_count": _usage_value(usage, "output_tokens", "completion_tokens"),
        "openai_status": status or "",
        "openai_incomplete_reason": incomplete_reason or "",
        "openai_reasoning_tokens": reasoning_tokens,
        # Empty means the provider did not report this metric.  Never convert absence to zero:
        # zero is a meaningful reported value (a cache miss), while empty is unavailable.
        "cached_input_tokens": cached_input_tokens,
        "effective_temperature": request.get("temperature"),
        "effective_seed": None,
        "effective_output_token_limit": request.get("max_output_tokens"),
        "dropped_parameters": dropped_parameters,
        "structured_output_enforced": response_schema is not None,
        "structured_output_schema_name": schema_name or "",
        "requested_num_ctx": None,
        "effective_num_ctx": None,
        "num_ctx_explicit": False,
        "think_requested": False,
        "think_honored": True,
        "think_fallback_used": False,
        "think_fallback_http_status": None,
    }
