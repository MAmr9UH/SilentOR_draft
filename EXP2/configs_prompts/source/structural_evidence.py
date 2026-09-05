#!/usr/bin/env python3
"""Cached, probe-independent structural evidence for Track B.

The rules in this module are generic and candidate-independent.  Requirement metadata determines
which declared variable family is in scope; the candidate inventory supplies the actual declaration.
Only a complete, metadata-derived mismatch in a declared variable type is authoritative enough to
bypass an LLM witness verifier. A weaker declared lower or upper bound is not a semantic
violation: the full candidate feasible region must be searched for a violating point.

Missing rows, ambiguous scope, and partial coverage are never FAIL because an equivalent
formulation or an unresolved target mapping may exist.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


RULE_TABLE = {
    "objective_direction": "exact objective sense is direct structural evidence",
    "declared_variable_type": (
        "complete metadata-scoped declared type mismatch is authoritative FAIL evidence"),
    "declared_lower_bound": (
        "a sufficient declaration proves PASS; a weaker declaration requires solver search"),
    "declared_upper_bound": (
        "a sufficient declaration proves PASS; a weaker declaration requires solver search"),
    "exact_visible_relation": "an exact normalized row is PASS; absence is UNRESOLVED",
}

AUTHORITATIVE_DECLARED_ATTRIBUTE_RULES = frozenset({"declared_variable_type"})

# Words that describe the property being checked rather than the semantic variable family.  They
# must not dominate scope resolution (for example, every metadata entry may contain "integer").
_PROPERTY_TOKENS = frozenset({
    "binary", "integer", "integral", "integrality", "continuous", "nonnegative",
    "nonnegativity", "non", "negative", "lower", "upper", "bound", "bounds", "domain",
    "type", "types", "variable", "variables", "value", "values", "must", "required",
    "requirement", "declared", "declaration", "number", "numbers", "count", "counts",
})
_STOP_TOKENS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "for", "is", "are", "be", "all",
    "each", "every", "with", "from", "on", "in", "by", "at", "if", "then", "that",
})


def _raw_tokens(value: Any) -> List[str]:
    return [token for token in re.findall(r"[a-z][a-z0-9]*", str(value).lower())
            if token not in _STOP_TOKENS]


def _singular(token: str) -> str:
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 4 and token.endswith("es") and not token.endswith(("ses", "xes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(value: Any, *, semantic: bool = False) -> set[str]:
    tokens = {_singular(token) for token in _raw_tokens(value)}
    if semantic:
        tokens = {token for token in tokens if token not in _PROPERTY_TOKENS and len(token) >= 2}
    return tokens


def _related_token(left: str, right: str) -> bool:
    """Conservative morphology without a benchmark vocabulary or external NLP dependency."""
    left, right = _singular(left), _singular(right)
    if left == right:
        return True
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 3 and longer.startswith(shorter):
        return True
    common = 0
    for a, b in zip(left, right):
        if a != b:
            break
        common += 1
    return common >= 4 and common / max(1, min(len(left), len(right))) >= 0.65


def _token_sets_related(left: Iterable[str], right: Iterable[str]) -> bool:
    return any(_related_token(a, b) for a in left for b in right)


def _norm_sense(value: Any) -> str:
    return {"<": "<=", ">": ">=", "=": "=="}.get(str(value).strip(), str(value).strip())


def _terms(items: Iterable[Dict[str, Any]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for item in items or []:
        name = str(item.get("var", ""))
        try:
            coefficient = float(item.get("coeff"))
        except (TypeError, ValueError):
            continue
        out[name] = out.get(name, 0.0) + coefficient
    return {name: value for name, value in out.items() if abs(value) > 1e-12}


def _same_relation(expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
    es, actual_sense = _norm_sense(expected.get("sense")), _norm_sense(actual.get("sense"))
    expected_terms, actual_terms = _terms(expected.get("lhs_terms", [])), _terms(
        actual.get("lhs_terms", []))
    try:
        expected_rhs, actual_rhs = float(expected.get("rhs")), float(actual.get("rhs"))
    except (TypeError, ValueError):
        return False
    if not expected_terms or set(expected_terms) != set(actual_terms):
        return False
    ratios = [
        actual_terms[name] / expected_terms[name]
        for name in expected_terms if abs(expected_terms[name]) > 1e-12
    ]
    if not ratios:
        return False
    scale = ratios[0]
    if abs(scale) <= 1e-12 or any(abs(value - scale) > 1e-9 for value in ratios):
        return False
    if scale < 0:
        actual_sense = {"<=": ">=", ">=": "<=", "==": "=="}.get(
            actual_sense, actual_sense)
    if es != actual_sense:
        return False
    return abs(actual_rhs - scale * expected_rhs) <= 1e-8 * max(
        1.0, abs(actual_rhs), abs(scale * expected_rhs))


def _objective_expected(requirement: Dict[str, Any]) -> str:
    text = (str(requirement.get("requirement_text", "")) + " " +
            str(requirement.get("category", ""))).lower()
    if any(word in text for word in ("minimize", "minimise", "minimum")):
        return "minimize"
    if any(word in text for word in ("maximize", "maximise", "maximum")):
        return "maximize"
    return ""


def _single_variable_bound(relation: Dict[str, Any]) -> Optional[Tuple[str, str, float]]:
    terms = _terms(relation.get("lhs_terms", []))
    if len(terms) != 1:
        return None
    name, coefficient = next(iter(terms.items()))
    try:
        rhs = float(relation.get("rhs"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coefficient) or not math.isfinite(rhs) or abs(coefficient) <= 1e-12:
        return None
    sense = _norm_sense(relation.get("sense"))
    bound = rhs / coefficient
    if sense == "<=":
        attribute = "upper_bound" if coefficient > 0 else "lower_bound"
    elif sense == ">=":
        attribute = "lower_bound" if coefficient > 0 else "upper_bound"
    else:
        return None
    return name, attribute, bound


def _expected_declared_attribute(requirement: Dict[str, Any],
                                 metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    text = (str(requirement.get("requirement_text", "")) + " " +
            str(requirement.get("category", ""))).lower()
    # An explicit binary demand is stronger than a nearby generic "integer" synonym.
    if re.search(r"\bbinary\b", text):
        return {"attribute": "vtype", "expected": "binary", "source": "requirement_text"}
    if re.search(r"\binteger\b|\bintegral\b|\bintegrality\b", text):
        return {"attribute": "vtype", "expected": "integer", "source": "requirement_text"}
    if re.search(r"\bcontinuous\b", text):
        return {"attribute": "vtype", "expected": "continuous", "source": "requirement_text"}
    if any(marker in text for marker in (
            "non_neg", "nonneg", "non-negative", "nonnegative")):
        return {"attribute": "lower_bound", "expected": 0.0,
                "source": "requirement_text"}
    bound = _single_variable_bound(metadata.get("requirement_relation") or {})
    if bound:
        variable, attribute, expected = bound
        return {"attribute": attribute, "expected": expected,
                "relation_variable": variable, "source": "requirement_relation"}
    return None


def _metadata_type_compatible(item: Dict[str, Any], expected: str) -> bool:
    declared = str(item.get("declared_type", "")).lower()
    if expected == "binary":
        return declared == "binary"
    if expected == "integer":
        return declared in {"integer", "binary"}
    if expected == "continuous":
        return declared == "continuous"
    return True


def _semantic_group_scores(requirement: Dict[str, Any],
                           groups: Sequence[Dict[str, Any]]) -> Dict[str, float]:
    requirement_tokens = _tokens(requirement.get("requirement_text", ""), semantic=True)
    if not requirement_tokens:
        return {str(item.get("variable", "")): 0.0 for item in groups}
    group_tokens = {
        str(item.get("variable", "")): _tokens(
            f"{item.get('variable', '')} {item.get('meaning', '')}", semantic=True)
        for item in groups
    }
    token_frequency: Dict[str, int] = {}
    for token in requirement_tokens:
        token_frequency[token] = sum(
            1 for tokens in group_tokens.values()
            if any(_related_token(token, candidate) for candidate in tokens))
    scores: Dict[str, float] = {}
    for name, tokens in group_tokens.items():
        score = 0.0
        for token in requirement_tokens:
            if any(_related_token(token, candidate) for candidate in tokens):
                score += 1.0 / max(1, token_frequency[token])
        scores[name] = score
    return scores


def _select_metadata_groups(requirement: Dict[str, Any], metadata: Dict[str, Any],
                            expected: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = [item for item in metadata.get("variables", []) if isinstance(item, dict)]
    relation_variable = str(expected.get("relation_variable", ""))
    if relation_variable:
        exact = [item for item in groups
                 if str(item.get("variable", "")) == relation_variable]
        if exact:
            return exact
        family = [
            item for item in groups
            if relation_variable.startswith(str(item.get("variable", "")) + "_")
            or relation_variable.startswith(str(item.get("variable", "")) + "[")
        ]
        if len(family) == 1:
            return family
        relation_tokens = _tokens(relation_variable)
        fuzzy = [item for item in groups if _token_sets_related(
            _tokens(item.get("variable", "")), relation_tokens)]
        return fuzzy if len(fuzzy) == 1 else []

    if expected.get("attribute") == "vtype":
        typed = [item for item in groups if _metadata_type_compatible(
            item, str(expected.get("expected", "")))]
        if typed:
            groups = typed

    scores = _semantic_group_scores(requirement, groups)
    maximum = max(scores.values(), default=0.0)
    if maximum > 0:
        # Keep every independently mentioned family while excluding groups that match only a very
        # common word. This handles requirements that explicitly name two or more variable families.
        threshold = maximum * 0.5
        return [item for item in groups
                if scores.get(str(item.get("variable", "")), 0.0) >= threshold]

    text = str(requirement.get("requirement_text", "")).lower()
    if len(groups) == 1 or re.search(r"\b(all|each|every)\b", text):
        return groups
    return []


def _group_inventory_matches(group_name: str,
                             inventory_variables: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    exact = []
    for variable in inventory_variables:
        name = str(variable.get("name", ""))
        if name == group_name or name.startswith(group_name + "_") or name.startswith(
                group_name + "["):
            exact.append(variable)
    if exact:
        return exact
    # Fuzzy family-name matching is permitted only for non-indexed contract group names.  It
    # resolves generic aliases such as allocation -> alloc_* without ever mapping one indexed
    # member to a different indexed member.
    if any(character.isdigit() for character in group_name):
        return []
    group_tokens = _tokens(group_name)
    return [
        variable for variable in inventory_variables
        if _token_sets_related(group_tokens, _tokens(str(variable.get("name", ""))))
    ]


def _metadata_scoped_targets(inventory: Dict[str, Any], requirement: Dict[str, Any],
                             metadata: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
    variables = [item for item in inventory.get("variables", []) if isinstance(item, dict)]
    groups = _select_metadata_groups(requirement, metadata, expected)
    relation_variable = str(expected.get("relation_variable", ""))
    if relation_variable:
        direct_targets = [item for item in variables
                          if str(item.get("name", "")) == relation_variable]
        group_name = str(groups[0].get("variable", "")) if len(groups) == 1 else ""
        group_accepts_target = bool(
            group_name and direct_targets and
            _group_inventory_matches(group_name, direct_targets))
        full = len(groups) == 1 and len(direct_targets) == 1 and group_accepts_target
        return {
            "source": "requirement_metadata_and_exact_relation_target",
            "metadata_target_groups": [str(item.get("variable", "")) for item in groups],
            "matched_variables_by_group": (
                {group_name: [relation_variable]} if full else {}),
            "unmatched_metadata_target_groups": ([] if full else
                ([group_name] if group_name else [relation_variable])),
            "target_variables": direct_targets if full else [],
            "scope_valid": full,
            "coverage": "FULL" if full else "NONE",
            "coverage_basis": "exact_relation_variable",
            "all_candidate_members_examined": full,
        }

    matched_by_group: Dict[str, List[str]] = {}
    targets_by_name: Dict[str, Dict[str, Any]] = {}
    unmatched: List[str] = []
    for group in groups:
        group_name = str(group.get("variable", ""))
        matches = _group_inventory_matches(group_name, variables)
        if not matches:
            unmatched.append(group_name)
            continue
        matched_by_group[group_name] = [str(item.get("name", "")) for item in matches]
        for item in matches:
            targets_by_name[str(item.get("name", ""))] = item
    full = bool(groups) and not unmatched and bool(targets_by_name)
    return {
        "source": "requirement_metadata",
        "metadata_target_groups": [str(item.get("variable", "")) for item in groups],
        "matched_variables_by_group": matched_by_group,
        "unmatched_metadata_target_groups": unmatched,
        "target_variables": list(targets_by_name.values()),
        "scope_valid": full,
        "coverage": "FULL" if full else ("PARTIAL" if targets_by_name else "NONE"),
        "coverage_basis": "all_candidate_declarations_in_every_metadata_target_group",
        "all_candidate_members_examined": full,
    }


def _numeric(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _vtype_satisfied(variable: Dict[str, Any], expected: str) -> bool:
    actual = str(variable.get("vtype", "")).upper()
    if expected == "binary":
        if actual == "B":
            return True
        lower, upper = _numeric(variable.get("lb")), _numeric(variable.get("ub"))
        return actual == "I" and lower is not None and upper is not None and lower >= 0 and upper <= 1
    if expected == "integer":
        return actual in {"I", "B"}
    if expected == "continuous":
        return actual == "C"
    return False


def _declared_attribute_record(inventory: Dict[str, Any], requirement: Dict[str, Any],
                               metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    expected = _expected_declared_attribute(requirement, metadata)
    if not expected:
        return None
    scope = _metadata_scoped_targets(inventory, requirement, metadata, expected)
    if scope["coverage"] != "FULL" or not scope["scope_valid"]:
        return {
            "status": "UNRESOLVED", "sufficient": False,
            "coverage": scope["coverage"], "requirement_complete_pass": False,
            "rule": "declared_attribute_scope_unresolved",
            "reason": "declared-attribute target scope is not complete in requirement metadata",
            "declared_attribute": expected["attribute"],
            "expected_value": expected["expected"], "target_scope": scope,
            "target_variables": [str(item.get("name", ""))
                                 for item in scope["target_variables"]],
            "authoritative_no_witness": False, "evidence_tier": 4,
        }

    offending: List[Dict[str, Any]] = []
    attribute = str(expected["attribute"])
    expected_value = expected["expected"]
    tolerance = 1e-9
    for variable in scope["target_variables"]:
        name = str(variable.get("name", ""))
        if attribute == "vtype":
            if not _vtype_satisfied(variable, str(expected_value)):
                offending.append({
                    "variable": name, "attribute": "vtype", "expected": expected_value,
                    "actual": str(variable.get("vtype", "")),
                    "lower_bound": variable.get("lb"), "upper_bound": variable.get("ub"),
                })
        elif attribute == "lower_bound":
            actual = _numeric(variable.get("lb"))
            if actual is None or actual < float(expected_value) - tolerance:
                offending.append({"variable": name, "attribute": "lower_bound",
                                  "expected": expected_value, "actual": actual})
        elif attribute == "upper_bound":
            actual = _numeric(variable.get("ub"))
            if actual is None or actual > float(expected_value) + tolerance:
                offending.append({"variable": name, "attribute": "upper_bound",
                                  "expected": expected_value, "actual": actual})

    failed = bool(offending)
    rule = {
        "vtype": "declared_variable_type",
        "lower_bound": "declared_lower_bound",
        "upper_bound": "declared_upper_bound",
    }[attribute]
    targets = [str(item.get("name", "")) for item in scope["target_variables"]]
    # A matching declaration is a sound proof that the semantic bound is enforced. A weaker
    # declaration is not a counterexample because other model constraints may imply a tighter
    # effective bound. Leave that case unresolved so the executable probe searches the complete
    # candidate feasible region. Declared variable-type mismatches remain authoritative.
    requires_solver = failed and attribute in {"lower_bound", "upper_bound"}
    return {
        "status": "UNRESOLVED" if requires_solver else ("FAIL" if failed else "PASS"),
        "sufficient": not requires_solver,
        "coverage": "FULL",
        "requirement_complete_pass": not failed,
        "rule": rule,
        "reason": (
            "declared bound is weaker than the semantic requirement; full feasible-region "
            "solver search is required: " + "; ".join(
                f"{item['variable']} {item['attribute']} expected={item['expected']} "
                f"actual={item.get('actual')}" for item in offending)
            if requires_solver else
            "declared attribute mismatch: " + "; ".join(
                f"{item['variable']} {item['attribute']} expected={item['expected']} "
                f"actual={item.get('actual')}" for item in offending)
            if failed else
            f"all {len(targets)} metadata-scoped targets satisfy {attribute}={expected_value}"
        ),
        "declared_attribute": attribute,
        "expected_value": expected_value,
        "target_scope": scope,
        "target_variables": targets,
        "offending_variables": offending,
        "authoritative_no_witness": failed and not requires_solver,
        "requires_solver_search": requires_solver,
        "evidence_tier": 4 if requires_solver else (1 if failed else 2),
        "taxonomy": "domain_or_bound_error" if failed and not requires_solver else "none",
    }


def is_authoritative_declared_attribute_failure(record: Dict[str, Any]) -> bool:
    """True only for a complete, correctly scoped deterministic declaration mismatch."""
    return bool(
        isinstance(record, dict) and
        record.get("status") == "FAIL" and
        record.get("sufficient") is True and
        record.get("coverage") == "FULL" and
        record.get("authoritative_no_witness") is True and
        record.get("rule") in AUTHORITATIVE_DECLARED_ATTRIBUTE_RULES and
        isinstance(record.get("target_scope"), dict) and
        record["target_scope"].get("scope_valid") is True and
        not record["target_scope"].get("unmatched_metadata_target_groups")
    )


def build_record(inventory: Dict[str, Any], requirement: Dict[str, Any],
                 metadata: Dict[str, Any], model_slice: Dict[str, Any]) -> Dict[str, Any]:
    """Build the one cached structural record for a candidate/requirement pair."""
    rid = str(requirement.get("requirement_id", ""))
    record: Dict[str, Any] = {
        "requirement_id": rid,
        "cache_scope": "candidate_requirement",
        "cache_key": hashlib.sha256(json.dumps({
            "inventory": model_slice.get("inventory_sha256", ""),
            "requirement": requirement,
            "metadata": metadata,
        }, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
        "status": "UNRESOLVED",
        "sufficient": False,
        "coverage": "NONE",
        "requirement_complete_pass": False,
        "decision_source": "structural_evidence",
        "rule": "",
        "reason": "",
        "authoritative_no_witness": False,
        "evidence_tier": 4,
        "observation": {
            "variables": model_slice.get("variables", []),
            "constraints": model_slice.get("constraints", []),
            "objective": model_slice.get("objective", {}),
            "slice_counts": model_slice.get("slice_counts", {}),
        },
    }

    expected_sense = _objective_expected(requirement)
    if expected_sense:
        actual = str(inventory.get("objective", {}).get("sense", "")).lower()
        passed = actual == expected_sense
        record.update({
            "status": "PASS" if passed else "FAIL",
            "sufficient": not passed,
            "coverage": "PARTIAL" if passed else "FULL",
            "requirement_complete_pass": False,
            "rule": "objective_direction",
            "evidence_tier": 2,
            "reason": (
                f"objective sense expected={expected_sense}, actual={actual}; matching direction "
                "does not prove complete objective terms or coefficients"
                if passed else
                f"objective sense expected={expected_sense}, actual={actual}"
            ),
        })
        return record

    declared = _declared_attribute_record(inventory, requirement, metadata)
    if declared is not None:
        record.update(declared)
        return record

    relation = metadata.get("requirement_relation") or {}
    if relation:
        for row in inventory.get("constraints", []):
            if _same_relation(relation, row):
                record.update({
                    "status": "PASS", "sufficient": True,
                    "coverage": "FULL", "requirement_complete_pass": True,
                    "rule": "exact_visible_relation", "evidence_tier": 2,
                    "reason": f"exact normalized relation found in row {row.get('name', '')}",
                })
                return record
        record.update({
            "rule": "exact_visible_relation", "evidence_tier": 4,
            "reason": "no exact row found; absence is weak structural evidence only",
        })
    else:
        record["reason"] = "no complete generic structural rule applies"
    return record


def assert_generic_rule_table() -> None:
    """Guard the policy table against benchmark-specific identifiers.

    The check intentionally targets identifier-shaped tokens rather than arbitrary substrings;
    ordinary words such as ``lower_bound`` contain ``r_`` but are not requirement IDs.
    """
    blob = json.dumps(RULE_TABLE, sort_keys=True).lower()
    forbidden_patterns = (
        r"\bproblem_id\b",
        r"\brequirement_id\b",
        r"\bp[0-9]+\b",
        r"\br_[a-z0-9_]+\b",
    )
    if any(re.search(pattern, blob) for pattern in forbidden_patterns):
        raise AssertionError("structural sufficiency rule table contains an identifier pattern")
