#!/usr/bin/env python3
"""Generic, identifier-free conservation semantics for Track B probes.

This module has no benchmark IDs, requirement IDs, domain-specific variable names, or gold
relations. It checks only that a conservation/flow/stock-transition probe uses equality and,
when complete candidate-independent metadata exists, that the proposed equation is algebraically
equivalent to that relation. Missing metadata never rejects a probe; the ordinary judges continue.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Iterable, List


FLOW_CATEGORIES = frozenset({
    "flow_balance", "conservation", "stock_transition", "inventory_balance",
})
CONSERVATION_CUES = (
    r"\bconserv(?:e|ed|ation)\b",
    r"\bbalance(?:d)?\b",
    r"\bopening\b.*\bclosing\b",
    r"\bstarting\b.*\bending\b",
    r"\binflows?\b.*\boutflows?\b",
    r"\bcarried?\b.*\bforward\b",
    r"\bavailable\b.*\bused\b.*\bremaining\b",
)


def _sense(value: Any) -> str:
    return {"=": "==", "<": "<=", ">": ">="}.get(
        str(value or "").strip(), str(value or "").strip())


def is_conservation_requirement(requirement: Dict[str, Any]) -> bool:
    category = str(requirement.get("category", "")).strip().lower()
    if category in FLOW_CATEGORIES:
        return True
    text = str(requirement.get("requirement_text", "")).lower()
    return any(re.search(pattern, text) for pattern in CONSERVATION_CUES)


def _relations(probe: Dict[str, Any]) -> List[Dict[str, Any]]:
    template = str(probe.get("probe_template", ""))
    params = probe.get("parameters") or {}
    if template == "linear_requirement_probe":
        return [{
            "lhs_terms": params.get("lhs_terms", []),
            "sense": params.get("sense"),
            "rhs": params.get("rhs"),
        }]
    if template == "constraint_row_probe":
        row = params.get("expected_row") or {}
        return [row] if isinstance(row, dict) else []
    if template == "indexed_constraint_family_probe":
        rows = params.get("expected_rows") or []
        return [row for row in rows if isinstance(row, dict)]
    return []


def _terms(items: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("var", ""))
        try:
            coefficient = float(item.get("coeff"))
        except (TypeError, ValueError):
            continue
        if not name or not math.isfinite(coefficient):
            continue
        result[name] = result.get(name, 0.0) + coefficient
    return {name: value for name, value in result.items() if abs(value) > 1e-12}


def _complete_relation(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        rhs = float(value.get("rhs"))
    except (TypeError, ValueError):
        return False
    return bool(_terms(value.get("lhs_terms", []))) and _sense(value.get("sense")) in {
        "<=", ">=", "=="
    } and math.isfinite(rhs)


def _same_relation(expected: Dict[str, Any], proposed: Dict[str, Any]) -> bool:
    expected_terms = _terms(expected.get("lhs_terms", []))
    proposed_terms = _terms(proposed.get("lhs_terms", []))
    if not expected_terms or set(expected_terms) != set(proposed_terms):
        return False
    ratios = [proposed_terms[name] / expected_terms[name] for name in expected_terms]
    scale = ratios[0]
    if abs(scale) <= 1e-12 or any(abs(value - scale) > 1e-9 for value in ratios):
        return False
    proposed_sense = _sense(proposed.get("sense"))
    if scale < 0:
        proposed_sense = {"<=": ">=", ">=": "<=", "==": "=="}.get(
            proposed_sense, proposed_sense)
    try:
        expected_rhs = float(expected.get("rhs"))
        proposed_rhs = float(proposed.get("rhs"))
    except (TypeError, ValueError):
        return False
    return (
        _sense(expected.get("sense")) == proposed_sense and
        abs(proposed_rhs - scale * expected_rhs) <= 1e-8 * max(
            1.0, abs(proposed_rhs), abs(scale * expected_rhs))
    )


def validate_conservation_probe(requirement: Dict[str, Any], metadata: Dict[str, Any],
                                probe: Dict[str, Any]) -> Dict[str, Any]:
    """Return PASS, REPAIR, CANNOT_VERIFY, or NOT_APPLICABLE."""
    if not is_conservation_requirement(requirement):
        return {"status": "NOT_APPLICABLE", "reason": "not a conservation requirement"}

    rows = _relations(probe)
    if not rows:
        return {
            "status": "CANNOT_VERIFY",
            "reason": "selected template does not expose a deterministic linear relation",
        }
    non_equal = [index for index, row in enumerate(rows) if _sense(row.get("sense")) != "=="]
    if non_equal:
        return {
            "status": "REPAIR",
            "reason": (
                "This requirement expresses conservation or balance. Use equality (sense == "
                "'==') and represent both sides in one normalized linear equation."
            ),
            "mismatched_rows": non_equal,
        }

    expected = metadata.get("requirement_relation") or {}
    if not _complete_relation(expected):
        return {
            "status": "CANNOT_VERIFY",
            "reason": (
                "equality is present, but candidate-independent metadata does not contain a "
                "complete relation for deterministic component comparison"
            ),
        }
    if len(rows) != 1 or not _same_relation(expected, rows[0]):
        expected_names = sorted(_terms(expected.get("lhs_terms", [])))
        proposed_names = sorted(_terms(rows[0].get("lhs_terms", []))) if rows else []
        return {
            "status": "REPAIR",
            "reason": (
                "The generated equality is not algebraically equivalent to the complete "
                "candidate-independent requirement relation. Repair only the missing, extra, "
                "or mis-signed terms and the right-hand side."
            ),
            "expected_variables": expected_names,
            "proposed_variables": proposed_names,
            "missing_variables": sorted(set(expected_names) - set(proposed_names)),
            "extra_variables": sorted(set(proposed_names) - set(expected_names)),
        }
    return {
        "status": "PASS",
        "reason": "equality and complete authoritative relation are algebraically aligned",
    }


def assert_identifier_free() -> None:
    blob = " ".join(FLOW_CATEGORIES) + " " + " ".join(CONSERVATION_CUES)
    forbidden = ("problem_id", "requirement_id", "p30", "year2", "cash")
    if any(value in blob.lower() for value in forbidden):
        raise AssertionError("conservation rule contains a benchmark or domain identifier")
