#!/usr/bin/env python3
"""Per-problem, per-requirement metadata for probe generation and judging.

Every probe-generation and judge call receives the SAME visible metadata bundle, derived
deterministically from the frozen problem record.  Giving agents variable and index semantics is
what lets them reason about "the assignment variable" or "for every customer" instead of guessing
from bare identifiers.

WHAT IS INCLUDED (all derivable from the visible problem statement / contract):
  * original requirement text, category, scope and quantifier
  * variable meanings (from model_contract.variables_keys and solution_schema)
  * index meanings and domains (parsed from key descriptions and data arrays)
  * variable type/domain metadata (integer/continuous/binary, bounds where stated)
  * every fixed parameter name and exact value, including nested dictionaries and arrays
  * probe-template semantics for the templates offered

WHAT IS EXCLUDED -- ENFORCED, NOT ADVISORY (see ``FORBIDDEN_METADATA_KEYS`` and ``scrub``):
  * mutation name / mutated field / any diff
  * candidate actual values (the metadata is candidate-INDEPENDENT by construction: it is built
    from the problem record only and never reads candidate code or the inventory)
  * gold-versus-candidate comparison, expected verdict, hidden checker outcome
  * gold objective / answer / reference solution

Note on terminal logging: mutant type (silent/loud) is printed for the human operator, but it is
NEVER part of this bundle and therefore never reaches a prompt.  ``assert_no_oracle_fields``
guards that.
"""
from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Sequence

# Keys that must never appear anywhere in a metadata bundle handed to an LLM.
FORBIDDEN_METADATA_KEYS = frozenset({
    "answer", "answer_rounded", "answer_detail", "reference_solution", "gold", "gold_value",
    "gold_objective", "GOLD_VALUE_STATUS", "GOLD_VALUE_WARNING",
    "checker_specs", "checker_functions", "formulation_audit_specs", "audit_data",
    "mutation", "mutation_name", "mutated_field", "mutation_location", "mutant_kind",
    "mutant_type", "is_mutant", "source_diff", "diff",
    "expected_verdict", "expected_diagnosis", "hidden_checker", "checker_outcome",
    "candidate_values", "candidate_actual", "gold_vs_candidate", "comparison",
})

_FORBIDDEN_SUBSTRINGS = ("gold", "mutant", "mutation", "expected_verdict", "checker_outcome",
                         "reference_solution", "answer")

# ---------------------------------------------------------------------------------------------
# Template semantics -- what each probe template MEANS. Shown to generators and judges so both
# reason about the same contract.
# ---------------------------------------------------------------------------------------------
TEMPLATE_SEMANTICS: Dict[str, str] = {
    "linear_requirement_probe":
        "One typed linear contract. comparison has terms/relation/rhs; ratio has REQUIRED "
        "numerator_terms and denominator_terms plus relation/bound; balance has REQUIRED "
        "inflow_terms, outflow_terms, and constant. The deterministic compiler converts it to "
        "a violation expression, requires a numeric rhs and canonical sense for comparison, and never supplies a "
        "missing field or zero denominator.",
    "constraint_row_probe":
        "One named constraint row of the candidate, compared after deterministic normalization. "
        "Requires expected_row with lhs_terms, sense, numeric rhs.",
    "indexed_constraint_family_probe":
        "A FAMILY of typed linear contracts, one per exact metadata index member. Select one exact "
        "index_set key and provide a unique member for every authoritative key. Coverage is checked "
        "against metadata, then a seeded solver sample maximizes each member's violation. Never "
        "collapse the family into a global sum.",
    "indexed_linear_family":
        "Same as indexed_constraint_family_probe: preserve 'for every index', expand every "
        "required member, never collapse into one global sum.",
    "implication_probe":
        "A typed gated contract: one exact binary gate variable, gate_value in {0,1}, and one typed "
        "comparison consequent. The gate and consequent form the implication's conjunction (AND) "
        "test. A violation is antecedent TRUE and consequent FALSE. If the "
        "gate is infeasible the result is VACUOUS_PASS/UNRESOLVED, never PASS. When a known "
        "capacity exists, prefer a complete linear comparison instead.",
    "check_objective_terms":
        "The objective's direction and its variable->coefficient mapping. Compare sense, the term "
        "set, each coefficient, and coverage. complete_coverage=true means extra objective terms "
        "are a failure; false means only the listed terms are required.",
    "check_variable_property":
        "A declared property of variables (integrality, binary, lower/upper bound). Every target "
        "variable in the required scope must be compared, not just one representative.",
    "not_probeable":
        "An honest refusal: the requirement cannot be expressed by any allowed template. Costs "
        "nothing and can never make the candidate fail.",
}

_QUANTIFIER_PATTERNS = (
    (r"\bfor (?:each|every|all)\b", "universal"),
    (r"\beach\b", "universal"),
    (r"\bevery\b", "universal"),
    (r"\bat least one\b", "existential"),
    (r"\bexactly one\b", "unique"),
    (r"\bno more than\b|\bat most\b", "bounded_above"),
    (r"\btotal\b|\boverall\b|\bsum of all\b", "aggregate"),
)


def _scope_and_quantifier(requirement_text: str) -> Dict[str, str]:
    """Derive the requirement's scope and quantifier from its own wording (visible source only)."""
    text = str(requirement_text or "")
    low = text.lower()
    quantifier = "unspecified"
    for pattern, label in _QUANTIFIER_PATTERNS:
        if re.search(pattern, low):
            quantifier = label
            break
    scope = "global"
    match = re.search(r"\bfor (?:each|every|all) ([a-z][a-z _-]{2,40})", low)
    if match:
        scope = f"per {match.group(1).strip()}"
    else:
        each_match = re.search(r"\beach ([a-z][a-z _-]{2,40})", low)
        if each_match:
            scope = f"per {each_match.group(1).strip()}"
    return {"quantifier": quantifier, "scope": scope}


def _variable_metadata(problem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Variable meanings, index meanings/domains and type hints from the visible contract."""
    contract = problem.get("model_contract") or {}
    keys = contract.get("variables_keys") or {}
    schema_props = (((problem.get("solution_schema") or {}).get("properties") or {})
                    .get("solution") or {}).get("properties") or {}
    out: List[Dict[str, Any]] = []
    for name, description in keys.items():
        desc = str(description)
        entry: Dict[str, Any] = {"variable": str(name), "meaning": desc}

        # index meanings / domains, parsed from the key description
        index_match = re.search(r"key '([^']*)'(?:\.\.'([^']*)')?", desc)
        if index_match:
            if index_match.group(2):
                entry["index_domain"] = f"{index_match.group(1)}..{index_match.group(2)}"
                entry["index_meaning"] = "single index over the listed range"
            else:
                key_form = index_match.group(1)
                entry["index_domain"] = key_form
                entry["index_meaning"] = (
                    "composite index" if "," in key_form else "single index")
        if "1-indexed" in desc:
            entry["indexing_base"] = 1
        restriction = re.search(r"only ([^)]*)", desc)
        if restriction:
            entry["index_restriction"] = restriction.group(1).strip()

        # type / domain hints
        low = desc.lower()
        # Type phrases are intentionally mutually exclusive.  v40 used shared descriptions such
        # as "integer worker, total, or binary method-choice variable" and the first occurrence
        # of the word "binary" incorrectly labelled every worker count as binary.  Ambiguous
        # descriptions now remain unspecified instead of being promoted to a stronger domain.
        type_hits = {
            "binary": bool(re.search(r"\bbinary\b|\bindicator\b", low)),
            "integer": bool(re.search(r"\binteger\b|\bintegral\b", low)),
            "continuous": bool(re.search(r"\bcontinuous\b", low)),
        }
        if type_hits["binary"] and not type_hits["integer"] and not type_hits["continuous"]:
            entry["declared_type"] = "binary"
        elif type_hits["integer"] and not type_hits["binary"] and not type_hits["continuous"]:
            entry["declared_type"] = "integer"
        elif type_hits["continuous"] and not type_hits["binary"] and not type_hits["integer"]:
            entry["declared_type"] = "continuous"
        elif "units" in low or "count" in low:
            entry["declared_type"] = "integer_or_continuous_units"
        else:
            entry["declared_type"] = "unspecified"
        entry["lower_bound_stated"] = (
            0 if any(token in low for token in (
                "nonnegative", "non-negative", "units", "amount", "count")) else None)

        described = schema_props.get(str(name)) or {}
        if described.get("description"):
            entry["solution_schema_description"] = str(described["description"])
        if described:
            entry["solution_schema_domain"] = {
                key: deepcopy(described[key])
                for key in ("type", "minimum", "maximum", "exclusiveMinimum",
                            "exclusiveMaximum", "enum", "minItems", "maxItems")
                if key in described
            }
        out.append(entry)
    return out


def _fixed_parameters(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Return every visible fixed parameter with its exact value.

    Earlier versions summarized arrays and reduced dictionaries to their keys.  That made numeric
    judge decisions impossible to audit and, for dictionary-valued parameters, removed the values
    entirely.  The visible data instance is already candidate-independent model input, so preserving
    it losslessly is both safe and necessary.
    """
    return deepcopy(problem.get("data_instance") or {})


def _value_shape(value: Any) -> Dict[str, Any]:
    """Describe a parameter's shape without replacing its authoritative value."""
    if isinstance(value, dict):
        return {
            "type": "dictionary",
            "cardinality": len(value),
            "keys": [str(key) for key in value.keys()],
            "value_shapes": {str(key): _value_shape(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
            "item_shapes": [_value_shape(item) for item in value],
        }
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if value is None:
        return {"type": "null"}
    return {"type": type(value).__name__}


def _fixed_parameter_metadata(problem: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(name): _value_shape(value)
        for name, value in (problem.get("data_instance") or {}).items()
    }


def _index_sets(problem: Dict[str, Any]) -> Dict[str, Any]:
    """Index sets implied by the data arrays, so 'for every i' has a concrete domain."""
    data = problem.get("data_instance") or {}
    lengths = {len(v) for v in data.values() if isinstance(v, list)}
    sets: Dict[str, Any] = {}
    for length in sorted(lengths):
        sets[f"size_{length}"] = {
            "cardinality": length,
            "one_indexed_members": [str(i) for i in range(1, length + 1)],
            "zero_indexed_members": [str(i) for i in range(length)],
            "arrays_of_this_length": sorted(k for k, v in data.items()
                                            if isinstance(v, list) and len(v) == length),
        }
        # Explicit bases remove the ambiguity that previously let a generator choose whichever
        # member list happened to match its output.  The compiler consumes one of these exact
        # authoritative sets and never infers coverage from generated rows.
        sets[f"size_{length}_one_indexed"] = {
            "cardinality": length,
            "members": [str(i) for i in range(1, length + 1)],
            "indexing_base": 1,
            "arrays_of_this_length": sorted(k for k, v in data.items()
                                            if isinstance(v, list) and len(v) == length),
        }
        sets[f"size_{length}_zero_indexed"] = {
            "cardinality": length,
            "members": [str(i) for i in range(length)],
            "indexing_base": 0,
            "arrays_of_this_length": sorted(k for k, v in data.items()
                                            if isinstance(v, list) and len(v) == length),
        }
    for name, value in data.items():
        if isinstance(value, dict):
            sets[f"dictionary_{name}"] = {
                "cardinality": len(value),
                "members": [str(key) for key in value.keys()],
                "meaning": f"explicit keys of fixed parameter {name}",
            }
    def add_nested(path: str, value: Any) -> None:
        if isinstance(value, dict):
            key = "dictionary_" + re.sub(r"[^A-Za-z0-9_]+", "_", path).strip("_")
            sets.setdefault(key, {
                "cardinality": len(value),
                "members": [str(member) for member in value.keys()],
                "meaning": f"explicit keys of fixed parameter {path}",
            })
            for child, item in value.items():
                add_nested(f"{path}.{child}" if path else str(child), item)
        elif isinstance(value, list):
            key = "array_" + re.sub(r"[^A-Za-z0-9_]+", "_", path).strip("_")
            sets.setdefault(key + "_one_indexed", {
                "cardinality": len(value), "members": [str(i) for i in range(1, len(value) + 1)],
                "indexing_base": 1, "meaning": f"positions of fixed parameter {path}",
            })
            sets.setdefault(key + "_zero_indexed", {
                "cardinality": len(value), "members": [str(i) for i in range(len(value))],
                "indexing_base": 0, "meaning": f"positions of fixed parameter {path}",
            })
            for index, item in enumerate(value):
                add_nested(f"{path}[{index}]", item)
    for name, value in data.items():
        add_nested(str(name), value)
    return sets


def _units_and_time(problem: Dict[str, Any], requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Expose the exact visible prose from which units and time meanings must be derived.

    We intentionally do not invent units.  Agents receive the complete source text and are told
    that an unstated unit or period remains unspecified.
    """
    description = str(problem.get("problem_description") or problem.get("description") or "")
    requirement_text = str(requirement.get("requirement_text", ""))
    time_tokens = sorted(set(re.findall(
        r"\b(?:year|month|week|day|hour|period|quarter|season)s?(?:\s+\d+)?\b",
        f"{description} {requirement_text}", flags=re.IGNORECASE)))
    unit_tokens = sorted(set(re.findall(
        r"\b(?:dollars?|euros?|pounds?|tons?|tonnes?|kilograms?|kg|liters?|litres?|"
        r"units?|vehicles?|trucks?|workers?|people|customers?|projects?)\b",
        f"{description} {requirement_text}", flags=re.IGNORECASE)))
    return {
        "source_problem_description": description,
        "source_requirement": requirement_text,
        "explicit_time_terms": time_tokens,
        "explicit_unit_terms": unit_tokens,
        "unstated_values_policy": "unverifiable; do not infer or invent",
    }


def _constraint_semantics(requirement_text: str) -> Dict[str, Any]:
    low = str(requirement_text or "").lower()
    cues: List[str] = []
    for pattern, label in (
        (r"must not exceed|cannot exceed|at most|upper bound|less than or equal|"
         r"\blimit of\b|<=", "upper_bound"),
        (r"at least|lower bound|greater than or equal|>=", "lower_bound"),
        (r"exactly|must equal|equals|=", "equality"),
        (r"\bfor (?:each|every|all)\b|\beach\b|\bevery\b", "indexed_universal"),
        (r"\bif\b.*\bthen\b|\bwhenever\b|\bimplies?\b", "implication"),
    ):
        if re.search(pattern, low):
            cues.append(label)
    return {
        "original_text_is_authoritative": True,
        "explicit_semantic_cues": cues,
        "silence_policy": "metadata silence neither confirms nor contradicts a numeric claim",
    }


def _content_tokens(value: Any) -> set[str]:
    return {
        token for token in re.findall(r"[a-z][a-z0-9]+", str(value).lower())
        if token not in {
            "the", "a", "an", "and", "or", "of", "to", "for", "must", "is", "are",
            "be", "at", "in", "on", "each", "every", "all",
        }
    }


def _numeric_leaves(value: Any, prefix: str = "") -> List[Dict[str, Any]]:
    leaves: List[Dict[str, Any]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            leaves.extend(_numeric_leaves(item, path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            path = f"{prefix}[{index}]"
            leaves.extend(_numeric_leaves(item, path))
    elif isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        leaves.append({"path": prefix, "value": float(value)})
    return leaves


def _best_variable(problem: Dict[str, Any], requirement_text: str,
                   required_tokens: Iterable[str] = ()) -> Optional[str]:
    variables = ((problem.get("model_contract") or {}).get("variables_keys") or {})
    req_tokens = _content_tokens(requirement_text) | set(required_tokens)
    ranked = []
    for name, meaning in variables.items():
        tokens = _content_tokens(name) | _content_tokens(meaning)
        score = len(req_tokens & tokens)
        ranked.append((score, str(name)))
    ranked.sort(reverse=True)
    if not ranked or ranked[0][0] <= 0:
        return None
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None
    return ranked[0][1]


def _explicit_numbers(text: str) -> List[float]:
    values: List[float] = []
    for token in re.findall(r"(?<![A-Za-z0-9_])-?\d+(?:,\d{3})*(?:\.\d+)?", str(text)):
        try:
            values.append(float(token.replace(",", "")))
        except ValueError:
            continue
    return values


def _requirement_relation(problem: Dict[str, Any],
                          requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Derive a reusable mathematical relation without requirement/problem identifiers.

    A relation is emitted only for generic semantic categories whose visible metadata provides
    every term and numeric value.  Failure to derive is ordinary and means later evidence stays
    UNRESOLVED; no name-pattern or requirement-ID fallback is used.
    """
    text = str(requirement.get("requirement_text", ""))
    category = str(requirement.get("category", "")).lower()
    data = problem.get("data_instance") or {}
    variables = ((problem.get("model_contract") or {}).get("variables_keys") or {})

    # Generic inventory identity:
    # ending[item] = initial[item] + production[item] - demand[item].
    if category == "inventory_balance":
        initial = data.get("initial_inventory")
        demand = data.get("demand")
        if isinstance(initial, dict) and isinstance(demand, dict):
            item_scores = []
            text_tokens = _content_tokens(text)
            for item in set(initial) & set(demand):
                item_scores.append((len(text_tokens & _content_tokens(item)), str(item)))
            item_scores.sort(reverse=True)
            if item_scores and item_scores[0][0] > 0 and (
                    len(item_scores) == 1 or item_scores[0][0] > item_scores[1][0]):
                item = item_scores[0][1]
                ending = next(
                    (str(name) for name in variables
                     if "ending" in _content_tokens(name)
                     and bool(_content_tokens(item) & _content_tokens(name))),
                    None)
                production = next(
                    (str(name) for name in variables
                     if any(token in _content_tokens(name) for token in ("produce", "production"))
                     and bool(_content_tokens(item) & _content_tokens(name))),
                    None)
                if ending and production:
                    rhs = float(initial[item]) - float(demand[item])
                    return {
                        "derivation": "generic_inventory_balance",
                        "lhs_terms": [
                            {"var": ending, "coeff": 1.0},
                            {"var": production, "coeff": -1.0},
                        ],
                        "sense": "==",
                        "rhs": 0.0 if rhs == 0.0 else rhs,
                        "governing_parameters": [
                            f"initial_inventory.{item}", f"demand.{item}",
                        ],
                        "governing_parameter_coefficients": {
                            f"initial_inventory.{item}": 1.0,
                            f"demand.{item}": -1.0,
                        },
                    }

    cues = _constraint_semantics(text)["explicit_semantic_cues"]
    if any(cue in cues for cue in ("upper_bound", "lower_bound")) or \
            category in {"variable_bound", "budget"}:
        numbers = _explicit_numbers(text)
        leaves = _numeric_leaves(data)
        rhs = numbers[-1] if numbers else None
        governing = [
            item["path"] for item in leaves
            if rhs is not None and
            abs(item["value"] - rhs) <= 1e-9 * max(1.0, abs(rhs))
        ]
        target = _best_variable(
            problem, text,
            required_tokens=set().union(*(_content_tokens(path) for path in governing))
            if governing else ())
        if numbers and target:
            # When prose gives a unit conversion ("40 hours = 2400 minutes"), the final number
            # is the normalized RHS used by the model.
            rhs = numbers[-1]
            sense = ">=" if "lower_bound" in cues else "<="
            return {
                "derivation": "generic_explicit_bound",
                "lhs_terms": [{"var": target, "coeff": 1.0}],
                "sense": sense,
                "rhs": rhs,
                "governing_parameters": governing,
                "governing_parameter_coefficients": {
                    path: 1.0 for path in governing
                },
            }
    return {}


def _big_m_preference(problem: Dict[str, Any], requirement: Dict[str, Any]) -> Dict[str, Any]:
    """Expose a generic linear-linking preference when all visible prerequisites exist.

    This does not construct a gold row.  It only records that the visible contract contains a
    binary gate and the requirement/data contains a finite numeric capacity, so the generator
    should prefer a complete linear comparison over an implication probe.
    """
    text = str(requirement.get("requirement_text", ""))
    category = str(requirement.get("category", "")).lower()
    if not any(token in (category + " " + text.lower()) for token in (
            "implication", "link", "activation", "setup", "fixed", "if ")):
        return {"has_binary_gate": False, "has_known_capacity": False,
                "prefer_complete_linear_form": False}
    variables = _variable_metadata(problem)
    binary = [item["variable"] for item in variables
              if item.get("declared_type") == "binary"]
    nonbinary = [item["variable"] for item in variables
                 if item.get("declared_type") not in {"binary", "unspecified"}]
    explicit = _explicit_numbers(text)
    leaves = _numeric_leaves(problem.get("data_instance") or {})
    requirement_tokens = _content_tokens(text)
    relevant_leaves = [
        item for item in leaves
        if requirement_tokens & _content_tokens(item.get("path", ""))]
    capacities = explicit or [float(item["value"]) for item in relevant_leaves]
    known = [value for value in capacities if math.isfinite(value) and value >= 0]
    return {
        "has_binary_gate": bool(binary),
        "has_known_capacity": bool(known),
        "prefer_complete_linear_form": bool(binary and nonbinary and known),
        "candidate_binary_gate_variables": binary,
        "candidate_flow_or_count_variables": nonbinary,
        "visible_capacity_values": known[:32],
        "routing_rule": (
            "prefer comparison flow - capacity*gate <= 0; implication is secondary"
            if binary and nonbinary and known else "ordinary template routing"),
    }


def build_metadata(problem: Dict[str, Any], requirement: Dict[str, Any],
                   allowed_templates: Sequence[str] = ()) -> Dict[str, Any]:
    """Assemble the visible metadata bundle for ONE requirement.

    Candidate-independent by construction: reads only the frozen problem record and the written
    requirement.  Never reads candidate code, the candidate inventory, or any oracle artifact.
    """
    scope = _scope_and_quantifier(requirement.get("requirement_text", ""))
    bundle = {
        "requirement_id": str(requirement.get("requirement_id", "")),
        "original_requirement": str(requirement.get("requirement_text", "")),
        "requirement_category": str(requirement.get("category", "")),
        "requirement_scope": scope["scope"],
        "requirement_quantifier": scope["quantifier"],
        "problem_type": str(problem.get("problem_type", "")),
        "variables": _variable_metadata(problem),
        "index_sets": _index_sets(problem),
        "fixed_parameters": _fixed_parameters(problem),
        "fixed_parameter_metadata": _fixed_parameter_metadata(problem),
        "units_and_time_periods": _units_and_time(problem, requirement),
        "constraint_semantics": _constraint_semantics(
            requirement.get("requirement_text", "")),
        "requirement_relation": _requirement_relation(problem, requirement),
        "big_m_preference": _big_m_preference(problem, requirement),
        "template_semantics": {t: TEMPLATE_SEMANTICS[t] for t in allowed_templates
                               if t in TEMPLATE_SEMANTICS} or dict(TEMPLATE_SEMANTICS),
    }
    return scrub(bundle)


def scrub(bundle: Any) -> Any:
    """Recursively drop any forbidden key. Defence in depth behind build_metadata's construction."""
    if isinstance(bundle, dict):
        cleaned = {}
        for key, value in bundle.items():
            low = str(key).lower()
            if key in FORBIDDEN_METADATA_KEYS or any(s in low for s in _FORBIDDEN_SUBSTRINGS):
                continue
            cleaned[key] = scrub(value)
        return cleaned
    if isinstance(bundle, list):
        return [scrub(v) for v in bundle]
    return bundle


def assert_no_oracle_fields(bundle: Dict[str, Any]) -> None:
    """Raise if any oracle-bearing key survived. Called before every metadata-carrying prompt."""
    blob = json.dumps(bundle, default=str).lower()
    for token in ("gold_objective", "reference_solution", "mutation_name", "mutated_field",
                  "expected_verdict", "checker_outcome", "mutant_kind", "mutant_type",
                  "source_diff"):
        if token in blob:
            raise AssertionError(f"metadata leakage: {token!r} present in bundle")


def render(bundle: Dict[str, Any]) -> str:
    """Compact, human-and-LLM readable rendering for prompt inclusion."""
    return json.dumps(bundle, ensure_ascii=False, indent=1, default=str)
