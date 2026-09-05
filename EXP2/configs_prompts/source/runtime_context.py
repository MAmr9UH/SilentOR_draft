#!/usr/bin/env python3
"""Context-budget accounting and fail-fast runtime diagnostics for evaluated LLM calls."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional


DEFAULT_CHARS_PER_TOKEN = 3.0
DEFAULT_SAFETY_TOKENS = 1024


class ContextBudgetError(RuntimeError):
    """An unchanged prompt cannot fit the explicitly configured model context."""


def conservative_token_estimate(text: str, chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> int:
    """Conservative tokenizer-independent estimate used before the provider sees the prompt."""
    ratio = max(1.0, float(chars_per_token))
    return max(1, int((len(text) + ratio - 1) // ratio))


def budget_record(prompt: str, *, num_predict: int, num_ctx: Optional[int],
                  safety_tokens: int = DEFAULT_SAFETY_TOKENS,
                  chars_per_token: float = DEFAULT_CHARS_PER_TOKEN) -> Dict[str, Any]:
    estimated = conservative_token_estimate(prompt, chars_per_token)
    requested = max(0, int(num_predict))
    safety = max(0, int(safety_tokens))
    effective = int(num_ctx) if num_ctx is not None else None
    required = estimated + requested + safety
    return {
        "prompt_character_count": len(prompt),
        "prompt_utf8_bytes": len(prompt.encode("utf-8")),
        "estimated_prompt_tokens": estimated,
        "requested_num_predict": requested,
        "safety_tokens": safety,
        "requested_num_ctx": effective,
        "required_context_tokens": required,
        "context_headroom_tokens": (
            effective - required if effective is not None else None),
        "context_budget_safe": (
            required <= effective if effective is not None else True),
        "token_estimator": f"ceil(characters/{float(chars_per_token):g})",
    }


def assert_prompt_fits(prompt: str, *, num_predict: int, num_ctx: Optional[int],
                       safety_tokens: int = DEFAULT_SAFETY_TOKENS,
                       chars_per_token: float = DEFAULT_CHARS_PER_TOKEN,
                       label: str = "model call") -> Dict[str, Any]:
    record = budget_record(
        prompt, num_predict=num_predict, num_ctx=num_ctx,
        safety_tokens=safety_tokens, chars_per_token=chars_per_token)
    if not record["context_budget_safe"]:
        raise ContextBudgetError(
            f"{label} is over context budget: estimated_prompt_tokens="
            f"{record['estimated_prompt_tokens']} + num_predict="
            f"{record['requested_num_predict']} + safety={record['safety_tokens']} > "
            f"num_ctx={record['requested_num_ctx']}. The unchanged prompt was not sent.")
    return record


def ollama_advertised_context(ollama_url: str, model: str,
                              timeout: int = 30) -> Dict[str, Any]:
    """Read the model's advertised maximum context from Ollama ``/api/show``."""
    parsed = urllib.parse.urlsplit(ollama_url)
    show_url = urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, "/api/show", "", ""))
    body = json.dumps({"model": model}).encode("utf-8")
    request = urllib.request.Request(
        show_url, data=body, headers={"Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    model_info = payload.get("model_info", {}) or {}
    candidates = {
        str(key): value for key, value in model_info.items()
        if str(key).endswith(".context_length")
    }
    values = []
    for value in candidates.values():
        try:
            values.append(int(value))
        except (TypeError, ValueError):
            pass
    advertised = max(values) if values else None
    return {
        "model": model,
        "show_url": show_url,
        "advertised_context_length": advertised,
        "context_length_fields": candidates,
    }


def verify_requested_context(ollama_url: str, model: str, requested_num_ctx: int) -> Dict[str, Any]:
    info = ollama_advertised_context(ollama_url, model)
    advertised = info["advertised_context_length"]
    requested = int(requested_num_ctx)
    if advertised is not None and requested > advertised:
        raise ContextBudgetError(
            f"requested num_ctx={requested} exceeds {model}'s advertised maximum "
            f"context={advertised}")
    return {
        **info,
        "requested_num_ctx": requested,
        "effective_num_ctx": requested,
        "verified": advertised is not None,
        "verification_method": "explicit request checked against Ollama /api/show",
    }
