#!/usr/bin/env python3
"""Exact model-visible request identities and in-memory Attempt-1 artifact reuse."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional


SCHEMA_VERSION = 1


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str)


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def request_identity(*, stage: str, prompt: str, response_schema: Any, model: str,
                     role: str, seed: Any, temperature: Any, output_token_limit: int,
                     provider_options: Optional[Dict[str, Any]] = None,
                     stage_inputs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Return the exact cryptographic identity used before any artifact is reused."""
    schema_text = _canonical(response_schema)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "stage": str(stage),
        "exact_prompt_sha256": sha256_text(prompt),
        "response_schema_sha256": sha256_text(schema_text),
        "model": str(model),
        "role": str(role),
        "seed": seed,
        "temperature": temperature,
        "output_token_limit": int(output_token_limit),
        "provider_options": dict(provider_options or {}),
        "stage_inputs": dict(stage_inputs or {}),
    }
    identity["cache_key"] = sha256_text(_canonical(identity))
    return identity


def reuse_record(identity: Dict[str, Any], cached: Dict[str, Any], *,
                 receiver_candidate: str, receiver_record: str) -> Dict[str, Any]:
    return {
        "reused": True,
        "reuse_source_candidate": cached.get("source_candidate", ""),
        "reuse_source_record": cached.get("source_record", ""),
        "receiver_candidate": str(receiver_candidate or ""),
        "receiver_record": str(receiver_record or ""),
        "cache_key": identity["cache_key"],
        "prompt_hash": identity["exact_prompt_sha256"],
        "schema_hash": identity["response_schema_sha256"],
        "reused_stages": [identity["stage"]],
        "execution_reused": False,
        "identity_audit": "EXACT_MATCH",
    }


def generated_record(identity: Dict[str, Any], *, candidate: str, record: str) -> Dict[str, Any]:
    return {
        "reused": False,
        "reuse_source_candidate": "",
        "reuse_source_record": "",
        "receiver_candidate": str(candidate or ""),
        "receiver_record": str(record or ""),
        "cache_key": identity["cache_key"],
        "prompt_hash": identity["exact_prompt_sha256"],
        "schema_hash": identity["response_schema_sha256"],
        "reused_stages": [],
        "execution_reused": False,
        "identity_audit": "GENERATED_NORMALLY",
    }
