#!/usr/bin/env python3
"""Freeze manifest for prompts, examples, rules, and decision settings (v10 audit item).

Before any evaluated run, every prompt template, synthetic example block, certification
rule table, and decision constant is hashed into ``frozen_assets/prompt_freeze_manifest.json``.
``run_exp2`` verifies the manifest at startup and refuses to run on a mismatch (set
``EXP2_ALLOW_UNFROZEN=1`` only for development), so results can always be traced to the
exact frozen configuration.  Nothing in the manifest derives from evaluation labels, mutant
metadata, or benchmark problems: it hashes code constants only.

Usage:
    python freeze_manifest.py --write    # (re)freeze after intentional changes
    python freeze_manifest.py           # verify; exit 1 on drift
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
MANIFEST_PATH = HERE / "configs" / "prompt_freeze_manifest.json"

FROZEN_MODULES = (
    "track_b", "track_b_localization", "request_identity", "common_runner",
    "requirement_provider", "runtime_context", "context_preflight", "llm_clients",
    "probe_engine", "probe_roundtrip", "probe_schemas", "judge_panels",
    "problem_metadata", "probe_forensics", "structural_evidence", "flow_semantics",
    "shadow_witness_architecture",
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _freezable(value) -> bool:
    if isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (tuple, list)):
        return all(_freezable(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _freezable(item)
                   for key, item in value.items())
    if isinstance(value, (set, frozenset)):
        return all(_freezable(item) for item in value)
    return False


def _canonical(value):
    if isinstance(value, (set, frozenset)):
        return sorted(_canonical(item) for item in value)
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {key: _canonical(item) for key, item in sorted(value.items())}
    return value


def collect() -> dict:
    entries = {}
    for module_name in FROZEN_MODULES:
        module = __import__(module_name)
        for name in sorted(dir(module)):
            if not name.isupper() or name.startswith("_"):
                continue
            value = getattr(module, name)
            if not _freezable(value):
                continue
            payload = json.dumps(_canonical(value), sort_keys=True, ensure_ascii=False,
                                 default=str)
            entries[f"{module_name}.{name}"] = _sha(payload)
    global_hash = _sha(json.dumps(entries, sort_keys=True))
    return {"schema_version": 1, "entries": entries, "global_hash": global_hash}


def verify() -> list:
    if not MANIFEST_PATH.is_file():
        return ["freeze manifest missing: run `python freeze_manifest.py --write`"]
    frozen = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    current = collect()
    problems = []
    frozen_entries = frozen.get("entries", {})
    for key, value in current["entries"].items():
        if key not in frozen_entries:
            problems.append(f"unfrozen new constant: {key}")
        elif frozen_entries[key] != value:
            problems.append(f"frozen constant changed: {key}")
    for key in frozen_entries:
        if key not in current["entries"]:
            problems.append(f"frozen constant removed: {key}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="(re)generate the manifest")
    args = parser.parse_args()
    if args.write:
        manifest = collect()
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True),
                                 encoding="utf-8")
        print(f"froze {len(manifest['entries'])} constants; "
              f"global={manifest['global_hash'][:16]}")
        return 0
    problems = verify()
    if problems:
        print(f"FREEZE VERIFICATION FAILED ({len(problems)}):")
        for item in problems:
            print("  -", item)
        return 1
    print("freeze manifest verified: all prompts, examples, rules, and settings unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
