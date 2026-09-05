#!/usr/bin/env python3
"""Strict JSON Schemas for every structured LLM stage in Track B."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


NUMBER = {"type": "number"}
STRING = {"type": "string"}
BOOL = {"type": "boolean"}
NULL = {"type": "null"}

TERM = {
    "type": "object",
    "additionalProperties": False,
    "required": ["var", "coeff"],
    "properties": {"var": STRING, "coeff": NUMBER},
}

RELATION = {
    "type": "object",
    "additionalProperties": False,
    "required": ["lhs_terms", "sense", "rhs"],
    "properties": {
        "lhs_terms": {"type": "array", "minItems": 1, "items": TERM},
        "sense": {"type": "string", "enum": ["<=", ">=", "=="]},
        "rhs": NUMBER,
    },
}

# v41 typed probe contracts.  The model chooses mathematical content; the deterministic compiler
# supplies execution tolerances and converts every form into the existing linear/implication
# solver path.  Required fields are never defaulted to zero.
COMPARISON_CONTRACT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["form", "terms", "relation", "rhs"],
    "properties": {
        "form": {"type": "string", "enum": ["comparison"]},
        "terms": {"type": "array", "minItems": 1, "items": TERM},
        "relation": {"type": "string", "enum": ["<=", ">=", "=="]},
        "rhs": NUMBER,
    },
}

RATIO_CONTRACT = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "form", "numerator_terms", "denominator_terms", "relation", "bound"],
    "properties": {
        "form": {"type": "string", "enum": ["ratio"]},
        "numerator_terms": {"type": "array", "minItems": 1, "items": TERM},
        "denominator_terms": {"type": "array", "minItems": 1, "items": TERM},
        "relation": {"type": "string", "enum": ["<=", ">=", "=="]},
        "bound": NUMBER,
    },
}

BALANCE_CONTRACT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["form", "inflow_terms", "outflow_terms", "constant"],
    "properties": {
        "form": {"type": "string", "enum": ["balance"]},
        "inflow_terms": {"type": "array", "minItems": 1, "items": TERM},
        "outflow_terms": {"type": "array", "minItems": 1, "items": TERM},
        "constant": NUMBER,
    },
}

LINEAR_CONTRACT = {
    "anyOf": [
        deepcopy(COMPARISON_CONTRACT),
        deepcopy(RATIO_CONTRACT),
        deepcopy(BALANCE_CONTRACT),
    ],
}

GATED_CONTRACT = {
    "type": "object",
    "additionalProperties": False,
    "required": ["form", "gate_variable", "gate_value", "consequent"],
    "properties": {
        "form": {"type": "string", "enum": ["gated"]},
        "gate_variable": STRING,
        "gate_value": {"type": "integer", "enum": [0, 1]},
        "consequent": deepcopy(COMPARISON_CONTRACT),
    },
}


def template_selector_schema(allowed_templates) -> Dict[str, Any]:
    allowed = list(dict.fromkeys(str(item) for item in allowed_templates))
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["selected_template", "reason"],
        "properties": {
            "selected_template": {"type": "string", "enum": allowed},
            "reason": STRING,
        },
    }


def _parameters_schema(template: str) -> Dict[str, Any]:
    if template == "check_variable_property":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["target_variables", "property", "expected_value"],
            "properties": {
                "target_variables": {
                    "type": "array", "minItems": 1, "items": STRING},
                "property": {
                    "type": "string",
                    "enum": ["vtype", "lower_bound", "upper_bound", "existence"]},
                "expected_value": {
                    "anyOf": [STRING, NUMBER, BOOL]},
            },
        }
    if template == "linear_requirement_probe":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["contract"],
            "properties": {
                "contract": deepcopy(LINEAR_CONTRACT),
            },
        }
    if template == "maximize_linear_violation":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["violation_expressions"],
            "properties": {
                "violation_expressions": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": [
                            "name", "linear_expression", "constant",
                            "witness_threshold"],
                        "properties": {
                            "name": STRING,
                            "linear_expression": {
                                "type": "array", "minItems": 1,
                                "items": TERM,
                            },
                            "constant": NUMBER,
                            "witness_threshold": NUMBER,
                        },
                    },
                },
            },
        }
    if template == "check_constraint_exists_by_terms":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["required_variable_names", "required_sense"],
            "properties": {
                "required_variable_names": {
                    "type": "array", "minItems": 1, "items": STRING},
                "required_sense": {
                    "type": "string", "enum": ["any", "<=", ">=", "=="]},
            },
        }
    if template == "constraint_row_probe":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["expected_row", "tolerance"],
            "properties": {
                "expected_row": deepcopy(RELATION),
                "tolerance": NUMBER,
            },
        }
    if template == "indexed_constraint_family_probe":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["index_set", "members"],
            "properties": {
                "index_set": STRING,
                "members": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object", "additionalProperties": False,
                        "required": ["index_key", "contract"],
                        "properties": {
                            "index_key": STRING,
                            "contract": deepcopy(LINEAR_CONTRACT),
                        },
                    },
                },
            },
        }
    if template == "implication_probe":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["contract"],
            "properties": {
                "contract": deepcopy(GATED_CONTRACT),
            },
        }
    if template == "check_objective_terms":
        return {
            "type": "object", "additionalProperties": False,
            "required": [
                "required_variable_names", "required_sense",
                "required_coefficients", "complete_coverage"],
            "properties": {
                "required_variable_names": {
                    "type": "array", "items": STRING},
                "required_sense": {
                    "type": "string", "enum": ["minimize", "maximize"]},
                "required_coefficients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["name", "coefficient"],
                        "properties": {
                            "name": STRING, "coefficient": NUMBER,
                        },
                    }},
                "complete_coverage": BOOL,
            },
        }
    if template == "not_probeable":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["reason"],
            "properties": {"reason": STRING},
        }
    raise ValueError(f"unsupported probe template schema: {template}")


def probe_schema(template: str, requirement_id: str) -> Dict[str, Any]:
    """Return the exact strict schema for one selected template and requirement."""

    if template == "objective_difference_probe":
        return {
            "type": "object", "additionalProperties": False,
            "required": ["probe_id", "requirement_id", "probe_template", "claim", "parameters"],
            "properties": {
                "probe_id": {"type": "string"},
                "requirement_id": {"enum": [requirement_id]},
                "probe_template": {"enum": ["objective_difference_probe"]},
                "claim": {"type": "string"},
                "parameters": {
                    "type": "object", "additionalProperties": False,
                    "required": ["required_objective"],
                    "properties": {
                        "required_objective": {
                            "type": "object", "additionalProperties": False,
                            "required": ["sense", "terms"],
                            "properties": {
                                "sense": {"enum": ["minimize", "maximize"]},
                                "terms": {
                                    "type": "array", "minItems": 1,
                                    "items": {
                                        "type": "object", "additionalProperties": False,
                                        "required": ["var", "coeff"],
                                        "properties": {"var": {"type": "string"},
                                                       "coeff": {"type": "number"}}}},
                                "constant": {"type": "number"}}},
                        "tolerance": {"type": "number"}}}}}
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "probe_id", "requirement_id", "probe_template", "claim", "parameters"],
        "properties": {
            "probe_id": STRING,
            "requirement_id": {
                "type": "string", "enum": [str(requirement_id)]},
            "probe_template": {
                "type": "string", "enum": [str(template)]},
            "claim": STRING,
            "parameters": _parameters_schema(str(template)),
        },
    }


def _replacement_schema() -> Dict[str, Any]:
    scalar = {"anyOf": [STRING, NUMBER, BOOL, NULL]}
    return {
        "anyOf": [
            NULL,
            {
                "type": "object", "additionalProperties": False,
                "required": ["path", "from", "to"],
                "properties": {"path": STRING, "from": scalar, "to": scalar},
            },
        ]
    }


def judge_decision_schema(requirement_id: str, judge_name: str) -> Dict[str, Any]:
    patch = {
        "type": "object", "additionalProperties": False,
        "required": [
            "terms_to_add", "terms_to_remove", "coefficients_to_replace",
            "constraint_sense_to_replace", "right_hand_side_to_replace",
            "property_to_replace", "expected_value_to_replace", "coverage_to_replace"],
        "properties": {
            "terms_to_add": {
                "type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["variable", "coefficient"],
                    "properties": {"variable": STRING, "coefficient": NUMBER}}},
            "terms_to_remove": {
                "type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["variable"], "properties": {"variable": STRING}}},
            "coefficients_to_replace": {
                "type": "array", "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["variable", "from", "to"],
                    "properties": {"variable": STRING, "from": NUMBER, "to": NUMBER}}},
            "constraint_sense_to_replace": _replacement_schema(),
            "right_hand_side_to_replace": _replacement_schema(),
            "property_to_replace": _replacement_schema(),
            "expected_value_to_replace": _replacement_schema(),
            "coverage_to_replace": _replacement_schema(),
        },
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["requirement_id", "judge", "verdict", "patch", "reason", "confidence"],
        "properties": {
            "requirement_id": {"type": "string", "enum": [str(requirement_id)]},
            "judge": {"type": "string", "enum": [str(judge_name)]},
            "verdict": {"type": "string", "enum": ["ACCEPT", "REPAIR"]},
            "patch": patch,
            "reason": STRING,
            "confidence": NUMBER,
        },
    }


def witness_verifier_schema() -> Dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["requirement_demands", "decisive_check", "reason", "decision"],
        "properties": {
            "requirement_demands": STRING,
            "decisive_check": STRING,
            "reason": STRING,
            "decision": {"type": "string", "enum": ["YES", "NO"]},
        },
    }


def root_cause_schema(requirement_ids) -> Dict[str, Any]:
    ids = list(dict.fromkeys(str(item) for item in requirement_ids))
    return {
        "type": "object", "additionalProperties": False,
        "required": [
            "decision", "primary_requirement_id", "ranked_requirement_ids",
            "collateral_requirement_ids", "reason"],
        "properties": {
            "decision": {"type": "string", "enum": ["RANKED"]},
            "primary_requirement_id": {"type": "string", "enum": ids},
            "ranked_requirement_ids": {
                "type": "array", "minItems": 1, "maxItems": len(ids),
                "items": {"type": "string", "enum": ids}},
            "collateral_requirement_ids": {
                "type": "array",
                "items": {"type": "string", "enum": ids}},
            "reason": STRING,
        },
    }
