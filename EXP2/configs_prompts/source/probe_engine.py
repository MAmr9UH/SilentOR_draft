#!/usr/bin/env python3
"""Shared deterministic probe engine for Exp 2.

The engine keeps a lossless model inventory internally.  Verifier prompts receive only a
requirement-specific slice.  A probe is never executed until its schema, identifiers, variable
names, and requirement/template compatibility have been validated.

Supported templates
-------------------
check_variable_property
    Structural check of exactly one property (vtype, lower bound, upper bound, or existence) on
    an explicit list of exact variable names. Integrality failures receive an ordinary-solution
    check followed by a target-only feasible fractional witness search.
maximize_linear_violation
    One or more linear violation expressions.  Equality requirements require two opposite
    expressions so both directions are tested.
check_constraint_exists_by_terms
    Legacy weak structural presence check. A missing row is a WARNING, never a failure.
linear_requirement_probe
    A safe linear relation (<=, >=, or ==). The engine derives the correct one- or two-sided
    violation objective and asks Gurobi for a witness.
constraint_row_probe
    Exact coefficient/sense/RHS inspection for one row. A mismatch is a WARNING because an
    algebraically equivalent formulation may exist.
indexed_constraint_family_probe
    Exact inspection of a list of indexed rows. Missing/mismatched members are warnings only.
implication_probe
    Safe feasibility search for an antecedent together with the negation of a consequent. This
    covers generic linking, activation, and implication logic without unrestricted Python.
check_objective_terms
    Objective direction is a strong structural fact. Missing terms/coefficient differences are
    warnings because auxiliary-variable equivalents may exist.
not_probeable
    Explicit abstention.  It is always UNKNOWN, never PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

PROBE_TIMEOUT = 30
GRB_LICENSE_FILE = os.environ.get("GRB_LICENSE_FILE", "")

SUPPORTED_TEMPLATES = {
    "check_variable_property",
    "maximize_linear_violation",
    "linear_requirement_probe",
    "check_constraint_exists_by_terms",
    "constraint_row_probe",
    "indexed_constraint_family_probe",
    "implication_probe",
    "check_objective_terms",
    "objective_difference_probe",
}

# Every requirement receives this same pool in this same order. The LLM selector chooses from
# mathematical structure; requirement wording and category never restrict or reorder the pool.
SEMANTIC_TEMPLATE_POOL = (
    "linear_requirement_probe",
    "implication_probe",
    "check_variable_property",
    "maximize_linear_violation",
    "constraint_row_probe",
    "indexed_constraint_family_probe",
    "check_constraint_exists_by_terms",
    "objective_difference_probe",
    "check_objective_terms",
)

STRUCTURAL_PROPERTY_TEMPLATES = {"check_variable_property"}

WEAK_STATIC_TEMPLATES = {
    "check_constraint_exists_by_terms",
    "constraint_row_probe",
}

SOLVER_WITNESS_TEMPLATES = {
    "maximize_linear_violation",
    "linear_requirement_probe",
    "implication_probe",
    "indexed_constraint_family_probe",
}


INTROSPECT_HARNESS = r'''
import json, os, sys
os.environ["GRB_LICENSE_FILE"] = os.environ.get("GRB_LICENSE_FILE", "")
code_path, data_path = sys.argv[1], sys.argv[2]
user_code = open(code_path, "r", encoding="utf-8").read()
data = json.load(open(data_path, "r", encoding="utf-8"))
try:
    import gurobipy as gp
    from gurobipy import GRB
    ns = {"__name__": "candidate"}
    exec(user_code, ns)
    if "build_model" not in ns:
        raise RuntimeError("candidate has no build_model(data)")
    built = ns["build_model"](data)
    model = built[0] if isinstance(built, tuple) else built
    model.setParam("OutputFlag", 0)
    model.update()
    variables = []
    for v in model.getVars():
        variables.append({
            "name": v.VarName,
            "vtype": v.VType,
            "lb": None if v.LB <= -1e100 else float(v.LB),
            "ub": None if v.UB >= 1e100 else float(v.UB),
        })
    constraints = []
    for c in model.getConstrs():
        row = model.getRow(c)
        constraints.append({
            "name": c.ConstrName,
            "sense": c.Sense,
            "rhs": float(c.RHS),
            "lhs_terms": [
                {"var": row.getVar(i).VarName, "coeff": float(row.getCoeff(i))}
                for i in range(row.size())
            ],
        })
    objective = model.getObjective()
    objective_terms = [
        {"var": objective.getVar(i).VarName, "coeff": float(objective.getCoeff(i))}
        for i in range(objective.size())
    ]
    objective_constant = float(getattr(objective, "getConstant", lambda: 0.0)())
    model.optimize()
    objective_value = None
    if getattr(model, "SolCount", 0) > 0:
        values = {v.VarName: float(v.X) for v in model.getVars()}
        for item in variables:
            item["value"] = values.get(item["name"])
        objective_value = float(model.ObjVal)
    print("===INTRO_JSON_START===")
    print(json.dumps({
        "schema_version": 2,
        "variables": variables,
        "constraints": constraints,
        "objective": {
            "sense": "minimize" if model.ModelSense == 1 else "maximize",
            "constant": objective_constant,
            "terms": objective_terms,
        },
        "ordinary_solution": {
            "status": int(model.Status),
            "objective_value": objective_value,
        },
    }))
except Exception as exc:
    print("===INTRO_JSON_START===")
    print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
'''


PROBE_LINEAR_HARNESS = r'''
import json, os, sys
os.environ["GRB_LICENSE_FILE"] = os.environ.get("GRB_LICENSE_FILE", "")
code_path, probe_path, data_path = sys.argv[1], sys.argv[2], sys.argv[3]
user_code = open(code_path, "r", encoding="utf-8").read()
probe = json.load(open(probe_path, "r", encoding="utf-8"))
data = json.load(open(data_path, "r", encoding="utf-8"))
try:
    import gurobipy as gp
    from gurobipy import GRB
    ns = {"__name__": "candidate"}
    exec(user_code, ns)
    built = ns["build_model"](data)
    model = built[0] if isinstance(built, tuple) else built
    model.setParam("OutputFlag", 0)
    model.setParam("FeasibilityTol", 1e-9)
    model.setParam("IntFeasTol", 1e-9)
    model.setParam("OptimalityTol", 1e-9)
    model.setParam("NumericFocus", 3)
    model.update()
    vmap = {v.VarName: v for v in model.getVars()}

    def full_model_replay(target_model, atol=1e-6):
        """Replay the incumbent witness against EVERY original constraint, bound, and
        integrality condition in exact Python arithmetic (defense in depth over the
        solver's own feasibility claim)."""
        worst_c = 0.0; worst_b = 0.0; frac = 0.0; offenders = []
        for c in target_model.getConstrs():
            row = target_model.getRow(c)
            lhs = 0.0
            for i in range(row.size()):
                lhs += float(row.getCoeff(i)) * float(row.getVar(i).X)
            rhs = float(c.RHS); s = str(c.Sense)
            if s == "<": v = lhs - rhs
            elif s == ">": v = rhs - lhs
            else: v = abs(lhs - rhs)
            if v > worst_c: worst_c = v
            if v > atol: offenders.append({"constraint": str(c.ConstrName), "violation": v})
        for var in target_model.getVars():
            x = float(var.X)
            b = max(float(var.LB) - x, x - float(var.UB), 0.0)
            if b > worst_b: worst_b = b
            if str(var.VType) in ("I", "B"):
                f = abs(x - round(x))
                if f > frac: frac = f
        unverified = int(getattr(target_model, "NumGenConstrs", 0) or 0) + \
                     int(getattr(target_model, "NumQConstrs", 0) or 0)
        feasible = (worst_c <= atol and worst_b <= atol and frac <= atol and unverified == 0)
        return {"feasible": bool(feasible),
                "max_constraint_violation": worst_c,
                "max_bound_violation": worst_b,
                "max_integrality_violation": frac,
                "checked_constraints": int(target_model.NumConstrs),
                "checked_variables": int(target_model.NumVars),
                "unverified_nonlinear_constraints": unverified,
                "tolerance": atol,
                "violated": offenders[:5]}

    params = probe.get("parameters", {}) or {}
    tests = params.get("violation_expressions") or [{
        "name": "violation",
        "linear_expression": params.get("linear_expression", []),
        "constant": params.get("constant", 0.0),
        "witness_threshold": params.get("witness_threshold", 1e-6),
    }]
    results = []
    calls = 0
    for test in tests:
        expr = gp.LinExpr()
        missing = []
        for term in test.get("linear_expression", []):
            name = str(term.get("var", ""))
            if name not in vmap:
                missing.append(name)
            else:
                expr += float(term.get("coeff", 0.0)) * vmap[name]
        if missing:
            raise RuntimeError("unknown variables: " + ", ".join(missing))
        expr += float(test.get("constant", 0.0))
        model.setObjective(expr, GRB.MAXIMIZE)
        model.optimize()
        calls += 1
        if model.Status != GRB.OPTIMAL:
            results.append({"name": test.get("name", "violation"), "status": "UNKNOWN",
                            "solver_status": int(model.Status)})
            continue
        value = float(model.ObjVal)
        threshold = max(0.0, float(test.get("witness_threshold", 1e-6)))
        expression_terms = test.get("linear_expression", [])
        replay = float(test.get("constant", 0.0)) + sum(
            float(term.get("coeff", 0.0)) * float(vmap[str(term.get("var", ""))].X)
            for term in expression_terms
        )
        scale = max(
            1.0,
            abs(float(test.get("constant", 0.0))),
            sum(abs(float(term.get("coeff", 0.0))) *
                max(1.0, abs(float(vmap[str(term.get("var", ""))].X)))
                for term in expression_terms),
        )
        margin = max(threshold, 10.0 * 1e-9 * scale)
        agreement_tolerance = max(1e-8, 50.0 * 1e-9 * scale)
        agrees = abs(value - replay) <= agreement_tolerance
        if not agrees:
            results.append({
                "name": test.get("name", "violation"), "status": "UNKNOWN",
                "solver_objective": value, "recomputed_violation": replay,
                "acceptance_margin": margin, "scale": scale,
                "arithmetic_replay_agrees": False,
                "post_validation_confirmed": False,
                "message": "solver objective and Python arithmetic replay disagree",
            })
            continue
        found = replay > margin
        replay_report = None
        if found:
            replay_report = full_model_replay(model)
            if not replay_report["feasible"]:
                results.append({
                    "name": test.get("name", "violation"), "status": "UNKNOWN",
                    "solver_objective": value, "recomputed_violation": replay,
                    "acceptance_margin": margin, "scale": scale,
                    "arithmetic_replay_agrees": True,
                    "post_validation_confirmed": False,
                    "full_model_replay": replay_report,
                    "message": "witness failed full original-model replay",
                })
                continue
        witness = {
            str(term.get("var", "")): float(vmap[str(term.get("var", ""))].X)
            for term in expression_terms
        }
        results.append({
            "name": test.get("name", "violation"),
            "status": "WITNESS_FOUND" if found else "NO_WITNESS",
            "full_model_replay": replay_report,
            "violation_value": replay,
            "solver_objective": value,
            "recomputed_violation": replay,
            "threshold": threshold,
            "acceptance_margin": margin,
            "scale": scale,
            "solver_feasibility_tolerance": 1e-9,
            "arithmetic_replay_agrees": True,
            "post_validation_confirmed": True,
            "variables": witness if found else {},
        })
    if any(x["status"] == "WITNESS_FOUND" for x in results):
        status = "WITNESS_FOUND"
    elif any(x["status"] == "UNKNOWN" for x in results):
        status = "UNKNOWN"
    else:
        status = "NO_WITNESS"
    print("===PROBE_JSON_START===")
    confirmed = bool(results) and all(x.get("post_validation_confirmed") is True
                                      for x in results)
    agrees = bool(results) and all(x.get("arithmetic_replay_agrees") is True
                                   for x in results)
    found_test = next((x for x in results if x["status"] == "WITNESS_FOUND"), None)
    print(json.dumps({"status": status, "tests": results, "solver_calls": calls,
                      "post_validation_confirmed": confirmed,
                      "arithmetic_replay_agrees": agrees,
                      "full_model_replay": (found_test or {}).get("full_model_replay")}))
except Exception as exc:
    print("===PROBE_JSON_START===")
    print(json.dumps({"status": "UNKNOWN", "message": f"{type(exc).__name__}: {exc}",
                      "solver_calls": 0}))
'''



PROBE_OBJECTIVE_DIFF_HARNESS = r"""
import json, os, sys
os.environ["GRB_LICENSE_FILE"] = os.environ.get("GRB_LICENSE_FILE", "")
code_path, probe_path, data_path = sys.argv[1], sys.argv[2], sys.argv[3]
user_code = open(code_path, "r", encoding="utf-8").read()
probe = json.load(open(probe_path, "r", encoding="utf-8"))
data = json.load(open(data_path, "r", encoding="utf-8"))
try:
    import gurobipy as gp
    from gurobipy import GRB
    ns = {"__name__": "candidate"}
    exec(user_code, ns)
    built = ns["build_model"](data)
    model = built[0] if isinstance(built, tuple) else built
    model.setParam("OutputFlag", 0)
    model.setParam("FeasibilityTol", 1e-9)
    model.setParam("IntFeasTol", 1e-9)
    model.setParam("OptimalityTol", 1e-9)
    model.setParam("NumericFocus", 3)
    model.update()
    vmap = {v.VarName: v for v in model.getVars()}
    params = probe.get("parameters", {}) or {}
    required = params.get("required_objective", {}) or {}
    tolerance = max(1e-9, float(params.get("tolerance", 1e-6)))

    # ---- 1. objective sense -------------------------------------------------------------
    candidate_sense = "minimize" if int(model.ModelSense) == 1 else "maximize"
    required_sense = str(required.get("sense", "")).lower()
    if required_sense not in ("minimize", "maximize"):
        raise RuntimeError("required objective sense missing or invalid")
    if candidate_sense != required_sense:
        print("===PROBE_JSON_START===")
        print(json.dumps({"status": "SENSE_MISMATCH", "solver_calls": 0,
                          "candidate_sense": candidate_sense,
                          "required_sense": required_sense,
                          "message": "candidate optimises %s but the requirement states %s"
                                     % (candidate_sense, required_sense)}))
        sys.exit(0)

    # ---- 2. resolve the required objective ----------------------------------------------
    terms = required.get("terms", []) or []
    missing = [str(t.get("var", "")) for t in terms if str(t.get("var", "")) not in vmap]
    if missing:
        raise RuntimeError("unresolved variables in required objective: " + ", ".join(missing))
    bad_coeff = [str(t.get("var", "")) for t in terms
                 if not isinstance(t.get("coeff"), (int, float))]
    if bad_coeff:
        raise RuntimeError("non-numeric coefficients: " + ", ".join(bad_coeff))
    required_expr = gp.LinExpr()
    for t in terms:
        required_expr += float(t["coeff"]) * vmap[str(t["var"])]
    required_expr += float(required.get("constant", 0.0) or 0.0)

    # ---- 3. d(x) = candidate objective - required objective ------------------------------
    candidate_expr = model.getObjective()
    if not isinstance(candidate_expr, gp.LinExpr):
        raise RuntimeError("candidate objective is not linear")
    diff = candidate_expr - required_expr

    def optimise(sense_flag, label):
        model.setObjective(diff, sense_flag)
        model.optimize()
        st = int(model.Status)
        if st == GRB.OPTIMAL:
            witness = {v.VarName: float(v.X) for v in model.getVars()
                       if abs(float(v.X)) > 1e-12}
            return {"name": label, "outcome": "OPTIMAL", "value": float(model.ObjVal),
                    "solver_status": st,
                    "witness": dict(list(witness.items())[:60])}
        if st in (GRB.UNBOUNDED, GRB.INF_OR_UNBD):
            return {"name": label, "outcome": "UNBOUNDED", "solver_status": st}
        if st == GRB.INFEASIBLE:
            return {"name": label, "outcome": "INFEASIBLE", "solver_status": st}
        return {"name": label, "outcome": "INCONCLUSIVE", "solver_status": st}

    hi = optimise(GRB.MAXIMIZE, "max_difference")
    lo = optimise(GRB.MINIMIZE, "min_difference")
    calls = 2
    outcomes = {hi["outcome"], lo["outcome"]}

    if "INFEASIBLE" in outcomes:
        # An empty feasible region makes d == 0 vacuous; never report agreement.
        status, message = "INCONCLUSIVE", "candidate feasible region is empty"
    elif "UNBOUNDED" in outcomes:
        status, message = "DIFFERENCE_FOUND", "objective difference is unbounded"
    elif "INCONCLUSIVE" in outcomes:
        status, message = "INCONCLUSIVE", "solver returned a non-optimal status"
    else:
        worst = max(abs(hi["value"]), abs(lo["value"]))
        if worst <= tolerance:
            status, message = "NO_DIFFERENCE", ""
        else:
            status, message = "DIFFERENCE_FOUND", (
                "objective difference reaches %.12g over the candidate feasible region" % worst)

    affine = None
    if hi.get("outcome") == "OPTIMAL" and lo.get("outcome") == "OPTIMAL":
        affine = {"max_difference": hi["value"], "min_difference": lo["value"],
                  "constant_offset": bool(abs(hi["value"] - lo["value"]) <= tolerance)}

    print("===PROBE_JSON_START===")
    print(json.dumps({"status": status, "solver_calls": calls, "tolerance": tolerance,
                      "candidate_sense": candidate_sense, "required_sense": required_sense,
                      "tests": [hi, lo], "affine_agreement": affine, "message": message}))
except Exception as exc:
    print("===PROBE_JSON_START===")
    print(json.dumps({"status": "INCONCLUSIVE",
                      "message": "%s: %s" % (type(exc).__name__, exc), "solver_calls": 0}))
"""


PROBE_IMPLICATION_HARNESS = r'''
import json, os, sys
os.environ["GRB_LICENSE_FILE"] = os.environ.get("GRB_LICENSE_FILE", "")
code_path, probe_path, data_path = sys.argv[1], sys.argv[2], sys.argv[3]
user_code = open(code_path, "r", encoding="utf-8").read()
probe = json.load(open(probe_path, "r", encoding="utf-8"))
data = json.load(open(data_path, "r", encoding="utf-8"))
try:
    import gurobipy as gp
    from gurobipy import GRB
    ns = {"__name__": "candidate"}
    exec(user_code, ns)
    params = probe.get("parameters", {}) or {}
    antecedent = params.get("antecedent", []) or []
    consequent = params.get("consequent", []) or []
    threshold = max(0.0, float(params.get("witness_threshold",
                                         params.get("epsilon", 1e-6))))

    def build():
        built = ns["build_model"](data)
        model = built[0] if isinstance(built, tuple) else built
        model.setParam("OutputFlag", 0)
        model.setParam("FeasibilityTol", 1e-9)
        model.setParam("IntFeasTol", 1e-9)
        model.setParam("OptimalityTol", 1e-9)
        model.setParam("NumericFocus", 3)
        model.update()
        return model, {v.VarName: v for v in model.getVars()}

    def full_model_replay(target_model, atol=1e-6):
        """Replay the incumbent witness against EVERY original constraint, bound, and
        integrality condition in exact Python arithmetic. The probe added only an
        objective, so this certifies the witness is feasible in the complete
        original candidate model."""
        worst_c = 0.0; worst_b = 0.0; frac = 0.0; offenders = []
        for c in target_model.getConstrs():
            row = target_model.getRow(c)
            lhs = 0.0
            for i in range(row.size()):
                lhs += float(row.getCoeff(i)) * float(row.getVar(i).X)
            rhs = float(c.RHS); s = str(c.Sense)
            if s == "<": v = lhs - rhs
            elif s == ">": v = rhs - lhs
            else: v = abs(lhs - rhs)
            if v > worst_c: worst_c = v
            if v > atol: offenders.append({"constraint": str(c.ConstrName), "violation": v})
        for var in target_model.getVars():
            x = float(var.X)
            b = max(float(var.LB) - x, x - float(var.UB), 0.0)
            if b > worst_b: worst_b = b
            if str(var.VType) in ("I", "B"):
                f = abs(x - round(x))
                if f > frac: frac = f
        unverified = int(getattr(target_model, "NumGenConstrs", 0) or 0) + \
                     int(getattr(target_model, "NumQConstrs", 0) or 0)
        feasible = (worst_c <= atol and worst_b <= atol and frac <= atol and unverified == 0)
        return {"feasible": bool(feasible),
                "max_constraint_violation": worst_c,
                "max_bound_violation": worst_b,
                "max_integrality_violation": frac,
                "checked_constraints": int(target_model.NumConstrs),
                "checked_variables": int(target_model.NumVars),
                "unverified_nonlinear_constraints": unverified,
                "tolerance": atol,
                "violated": offenders[:5]}

    def expression(relation, vmap):
        expr = gp.LinExpr()
        for term in relation.get("lhs_terms", []):
            expr += float(term.get("coeff", 0.0)) * vmap[str(term.get("var", ""))]
        return expr

    def add_relation(model, vmap, relation):
        expr = expression(relation, vmap)
        sense = str(relation.get("sense", "")).strip()
        rhs = float(relation.get("rhs", 0.0))
        if sense in ("<=", "<"):
            model.addConstr(expr <= rhs)
        elif sense in (">=", ">"):
            model.addConstr(expr >= rhs)
        else:
            model.addConstr(expr == rhs)

    def relation_residual(relation, vmap, direction=None):
        expr = expression(relation, vmap)
        sense = str(relation.get("sense", "")).strip()
        rhs = float(relation.get("rhs", 0.0))
        if sense in ("<=", "<") or direction == "above":
            return expr - rhs, 1.0
        if sense in (">=", ">") or direction == "below":
            return rhs - expr, -1.0
        raise ValueError("equality residual requires above/below direction")

    def replay_relation(relation, values):
        lhs = sum(float(term.get("coeff", 0.0)) *
                  float(values[str(term.get("var", ""))])
                  for term in relation.get("lhs_terms", []))
        rhs = float(relation.get("rhs", 0.0))
        sense = str(relation.get("sense", "")).strip()
        scale = max(1.0, abs(rhs), sum(
            abs(float(term.get("coeff", 0.0))) *
            max(1.0, abs(float(values[str(term.get("var", ""))])))
            for term in relation.get("lhs_terms", [])))
        tol = max(1e-8, 10.0 * 1e-9 * scale)
        if sense in ("<=", "<"):
            residual = lhs - rhs
            satisfied = residual <= tol
        elif sense in (">=", ">"):
            residual = rhs - lhs
            satisfied = residual <= tol
        else:
            residual = abs(lhs - rhs)
            satisfied = residual <= tol
        return {"lhs": lhs, "rhs": rhs, "sense": sense, "residual": residual,
                "scale": scale, "tolerance": tol, "satisfied": satisfied}

    # A conjunction A => (B1 and ... and Bn) is violated when A holds and the *actual violation
    # residual* of any Bj is positive.  We maximize that residual directly; no epsilon-feasibility
    # construction is used.
    branches = []
    for idx, relation in enumerate(consequent):
        if str(relation.get("sense", "")).strip() in ("=", "=="):
            branches.extend([(idx, "below", relation), (idx, "above", relation)])
        else:
            branches.append((idx, "violate", relation))

    calls = 0
    results = []
    for idx, direction, relation in branches:
        model, vmap = build()
        for item in antecedent:
            add_relation(model, vmap, item)
        residual_expr, multiplier = relation_residual(
            relation, vmap, direction if direction in ("above", "below") else None)
        model.setObjective(residual_expr, GRB.MAXIMIZE)
        model.optimize()
        calls += 1
        if model.Status == GRB.OPTIMAL:
            values = {v.VarName: float(v.X) for v in model.getVars()}
            consequent_replay = replay_relation(relation, values)
            if direction == "below":
                replay = consequent_replay["rhs"] - consequent_replay["lhs"]
            elif direction == "above":
                replay = consequent_replay["lhs"] - consequent_replay["rhs"]
            elif str(relation.get("sense", "")).strip() in ("<=", "<"):
                replay = consequent_replay["lhs"] - consequent_replay["rhs"]
            else:
                replay = consequent_replay["rhs"] - consequent_replay["lhs"]
            scale = consequent_replay["scale"]
            margin = max(threshold, 10.0 * 1e-9 * scale)
            agreement_tolerance = max(1e-8, 50.0 * 1e-9 * scale)
            solver_value = float(model.ObjVal)
            agrees = abs(solver_value - replay) <= agreement_tolerance
            antecedent_replay = [replay_relation(item, values) for item in antecedent]
            antecedent_ok = all(item["satisfied"] for item in antecedent_replay)
            confirmed = agrees and antecedent_ok
            found = confirmed and replay > margin
            test = {
                "consequent_index": idx, "violation_direction": direction,
                "status": "WITNESS_FOUND" if found else "NO_WITNESS",
                "solver_objective": solver_value, "recomputed_violation": replay,
                "acceptance_margin": margin, "witness_threshold": threshold,
                "scale": scale, "solver_feasibility_tolerance": 1e-9,
                "arithmetic_replay_agrees": agrees,
                "antecedent_post_validation": antecedent_replay,
                "antecedent_satisfied": antecedent_ok,
                "post_validation_confirmed": confirmed,
            }
            if found:
                replay_report = full_model_replay(model)
                test["full_model_replay"] = replay_report
                if not replay_report["feasible"]:
                    found = False
                    test["status"] = "UNKNOWN"
                    test["post_validation_confirmed"] = False
                    test["message"] = "witness failed full original-model replay"
            if found:
                relevant = {str(term.get("var", ""))
                            for rel in [*antecedent, relation]
                            for term in rel.get("lhs_terms", [])}
                test["witness"] = {"variables": {name: values[name]
                                                   for name in sorted(relevant)}}
            results.append(test)
        elif model.Status in (GRB.INFEASIBLE, GRB.INF_OR_UNBD):
            results.append({"consequent_index": idx, "violation_direction": direction,
                            "status": "NO_WITNESS", "antecedent_infeasible": True,
                            "arithmetic_replay_agrees": True,
                            "post_validation_confirmed": True})
        else:
            print("===PROBE_JSON_START===")
            print(json.dumps({"status": "UNKNOWN", "solver_calls": calls,
                              "message": f"solver status {model.Status}"}))
            sys.exit(0)
    found = next((item for item in results if item["status"] == "WITNESS_FOUND"), None)
    replay_blocked = any(str(item.get("message", "")).startswith(
        "witness failed full original-model replay") for item in results)
    confirmed = bool(results) and all(item.get("post_validation_confirmed") is True
                                      for item in results)
    agrees = bool(results) and all(item.get("arithmetic_replay_agrees") is True
                                   for item in results)
    if found:
        overall = "WITNESS_FOUND"
    elif replay_blocked:
        overall = "UNKNOWN"
    elif results and all(item.get("antecedent_infeasible") is True for item in results):
        # The implication was never exercised.  A vacuous truth is not positive evidence that the
        # candidate enforces the requirement.
        overall = "VACUOUS_PASS"
    else:
        overall = "NO_WITNESS"
    output = {"status": overall,
              "solver_calls": calls, "tests": results,
              "post_validation_confirmed": confirmed,
              "arithmetic_replay_agrees": agrees}
    if found:
        output.update({"violated_consequent_index": found["consequent_index"],
                       "violation_direction": found["violation_direction"],
                       "witness": found.get("witness", {}),
                       "recomputed_violation": found.get("recomputed_violation"),
                       "acceptance_margin": found.get("acceptance_margin"),
                       "full_model_replay": found.get("full_model_replay")})
    print("===PROBE_JSON_START===")
    print(json.dumps(output))
except Exception as exc:
    print("===PROBE_JSON_START===")
    print(json.dumps({"status": "UNKNOWN", "message": f"{type(exc).__name__}: {exc}",
                      "solver_calls": 0}))
'''


PROBE_FRAC_HARNESS = r'''
import json, math, os, sys
os.environ["GRB_LICENSE_FILE"] = os.environ.get("GRB_LICENSE_FILE", "")
code_path, probe_path, data_path = sys.argv[1], sys.argv[2], sys.argv[3]
user_code = open(code_path, "r", encoding="utf-8").read()
probe = json.load(open(probe_path, "r", encoding="utf-8"))
data = json.load(open(data_path, "r", encoding="utf-8"))
try:
    import gurobipy as gp
    from gurobipy import GRB
    ns = {"__name__": "candidate"}
    exec(user_code, ns)
    built = ns["build_model"](data)
    model = built[0] if isinstance(built, tuple) else built
    model.setParam("OutputFlag", 0)
    model.update()
    target_names = probe.get("parameters", {}).get("target_variables", []) or []
    target_set = set(target_names)
    targeted = [v for v in model.getVars() if v.VarName in target_set]
    if not targeted:
        print("===PROBE_JSON_START===")
        print(json.dumps({"status": "UNKNOWN", "message": "no target variables", "solver_calls": 0}))
        sys.exit(0)

    # IMPORTANT: preserve every candidate variable domain.  A structurally wrong target is
    # already continuous in the candidate.  Correct, unrelated integer/binary variables remain
    # integer/binary throughout this witness search.
    tent = []
    for idx, var in enumerate(targeted):
        lower = var.LB if var.LB > -GRB.INFINITY else -1e6
        upper = var.UB if var.UB < GRB.INFINITY else 1e6
        anchor = model.addVar(vtype=GRB.INTEGER, lb=math.ceil(lower - 1),
                              ub=math.floor(upper), name=f"__target_anchor_{idx}")
        frac = model.addVar(lb=0.0, ub=1.0, name=f"__target_frac_{idx}")
        reward = model.addVar(lb=0.0, ub=0.5, name=f"__target_tent_{idx}")
        model.addConstr(var == anchor + frac)
        model.addConstr(reward <= frac)
        model.addConstr(reward <= 1.0 - frac)
        tent.append(reward)
    model.setObjective(gp.quicksum(tent), GRB.MAXIMIZE)
    model.setParam("TimeLimit", 10)
    model.optimize()
    tolerance = float(probe.get("parameters", {}).get("fractional_tolerance", 1e-6))
    if model.Status != GRB.OPTIMAL:
        print("===PROBE_JSON_START===")
        print(json.dumps({"status": "UNKNOWN", "message": f"solver status {model.Status}",
                          "solver_calls": 1}))
        sys.exit(0)
    fractional = {v.VarName: round(float(v.X), 8) for v in targeted
                  if abs(v.X - round(v.X)) > tolerance}
    status = "WITNESS_FOUND" if fractional else "NO_WITNESS"
    print("===PROBE_JSON_START===")
    print(json.dumps({"status": status, "solver_calls": 1,
                      "witness": {"fractional_variables": fractional}}))
except Exception as exc:
    print("===PROBE_JSON_START===")
    print(json.dumps({"status": "UNKNOWN", "message": f"{type(exc).__name__}: {exc}",
                      "solver_calls": 0}))
'''


def replay_linear_relation(relation: Dict[str, Any], values: Dict[str, float], *,
                           direction: Optional[str] = None,
                           solver_value: Optional[float] = None,
                           witness_threshold: float = 1e-6,
                           feasibility_tolerance: float = 1e-9) -> Dict[str, Any]:
    """Independently replay a relation/violation using plain Python arithmetic.

    This helper is also used by the numerical regression fixtures.  It intentionally has no
    access to candidate labels or benchmark answers.
    """
    lhs = 0.0
    scale_terms = 0.0
    missing = []
    for term in relation.get("lhs_terms", []):
        name = str(term.get("var", ""))
        if name not in values:
            missing.append(name)
            continue
        coefficient = float(term.get("coeff", 0.0))
        value = float(values[name])
        lhs += coefficient * value
        scale_terms += abs(coefficient) * max(1.0, abs(value))
    if missing:
        return {"confirmed": False, "arithmetic_replay_agrees": False,
                "missing_variables": missing, "reason": "missing witness variables"}
    rhs = float(relation.get("rhs", 0.0))
    sense = _normalize_sense(relation.get("sense"))
    if direction == "above" or (direction is None and sense == "<="):
        violation = lhs - rhs
    elif direction == "below" or (direction is None and sense == ">="):
        violation = rhs - lhs
    elif sense == "==":
        violation = abs(lhs - rhs)
    else:
        return {"confirmed": False, "arithmetic_replay_agrees": False,
                "reason": f"unsupported relation sense/direction: {sense}/{direction}"}
    scale = max(1.0, abs(rhs), scale_terms)
    margin = max(float(witness_threshold), 10.0 * float(feasibility_tolerance) * scale)
    agreement_tolerance = max(1e-8, 50.0 * float(feasibility_tolerance) * scale)
    agrees = (solver_value is None or
              abs(float(solver_value) - violation) <= agreement_tolerance)
    return {
        "confirmed": bool(agrees and violation > margin),
        "arithmetic_replay_agrees": bool(agrees),
        "lhs": lhs, "rhs": rhs, "sense": sense, "direction": direction,
        "recomputed_violation": violation, "acceptance_margin": margin,
        "scale": scale, "agreement_tolerance": agreement_tolerance,
    }


def _run_harness(harness: str, args: List[str]) -> Dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(harness)
        harness_path = f.name
    env = os.environ.copy()
    env["GRB_LICENSE_FILE"] = GRB_LICENSE_FILE
    try:
        proc = subprocess.run([sys.executable, harness_path] + args, capture_output=True,
                              text=True, timeout=PROBE_TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return {"status": "UNKNOWN", "message": f"timeout after {PROBE_TIMEOUT}s"}
    finally:
        try:
            os.unlink(harness_path)
        except OSError:
            pass
    for marker in ("===INTRO_JSON_START===", "===PROBE_JSON_START==="):
        if marker in proc.stdout:
            tail = proc.stdout.split(marker, 1)[1].strip()
            try:
                return json.loads(tail.splitlines()[0] if tail else "{}")
            except Exception:
                return {"status": "UNKNOWN", "message": "unparseable harness output"}
    return {"status": "UNKNOWN", "message": "missing harness marker",
            "stderr": proc.stderr[-1000:], "returncode": proc.returncode}


def _write_tmp(text: str, suffix: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(text)
        return f.name


def introspect(candidate_code: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build, solve, and return the complete lossless model inventory."""
    code_path = _write_tmp(candidate_code, ".py")
    data_path = _write_tmp(json.dumps(_safe_problem_data(data)), ".json")
    try:
        result = _run_harness(INTROSPECT_HARNESS, [code_path, data_path])
        if "error" not in result and result.get("schema_version") != 2:
            result["error"] = "unsupported inventory schema"
        return result
    finally:
        for path in (code_path, data_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def inventory_hash(inventory: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":"))
                          .encode("utf-8")).hexdigest()


def _safe_problem_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal/answer fields before data is stored or sent to a probe harness."""
    forbidden = {"answer", "answer_rounded", "_gold_objective", "reference_solution",
                 "injected_requirement", "mutation", "witness", "checker_specs",
                 "formulation_audit_specs"}
    return {k: v for k, v in (data or {}).items() if str(k).lower() not in forbidden}


def _tokens(text: str) -> set[str]:
    stop = {"the", "a", "an", "and", "or", "of", "to", "for", "must", "each", "all",
            "is", "are", "be", "with", "than", "that", "this", "requirement"}
    return {x for x in re.findall(r"[a-z][a-z0-9]+", str(text).lower()) if x not in stop}


def _var_prefix(name: str) -> str:
    return re.sub(r"(?:_?\d+)+$", "", name).rstrip("_") or name


def requirement_inventory_slice(inventory: Dict[str, Any], requirement: Dict[str, Any],
                                problem_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact, requirement-specific, coefficient-preserving inventory slice.

    The selected pilot models are small.  When lexical selection is uncertain, the function
    includes the complete model component instead of silently dropping information.
    """
    if "error" in inventory:
        return {"error": inventory["error"]}
    rid = str(requirement.get("requirement_id", ""))
    rtext = str(requirement.get("requirement_text", ""))
    category = str(requirement.get("category", ""))
    toks = _tokens(" ".join((rid, rtext, category)))
    variables = list(inventory.get("variables", []))
    constraints = list(inventory.get("constraints", []))
    objective = dict(inventory.get("objective", {}))

    domain_like = any(x in category.lower() for x in
                      ("integr", "domain", "binary", "non_neg", "nonneg", "bound"))
    objective_like = _is_objective_operation_requirement(requirement)

    def var_relevant(var: Dict[str, Any]) -> bool:
        name_tokens = _tokens(var.get("name", "")) | {_var_prefix(str(var.get("name", "")))}
        return bool(toks & name_tokens)

    selected_vars = [v for v in variables if var_relevant(v)]
    if domain_like:
        # Domain language often names semantic groups ("all investments", "shipments") that do
        # not lexically resemble compact variable names. Keep all declarations in the slice so
        # the verifier can independently choose the governed subset.
        selected_vars = variables

    def constraint_relevant(con: Dict[str, Any]) -> bool:
        name_tokens = _tokens(con.get("name", ""))
        term_tokens = set()
        for term in con.get("lhs_terms", []):
            term_tokens |= _tokens(term.get("var", ""))
        return bool(toks & (name_tokens | term_tokens))

    selected_cons = [] if domain_like else [c for c in constraints if constraint_relevant(c)]
    if not domain_like and not selected_cons and not objective_like:
        selected_cons = constraints

    selected_names = {t.get("var") for c in selected_cons for t in c.get("lhs_terms", [])}
    selected_names |= {v.get("name") for v in selected_vars}
    if objective_like:
        selected_names |= {t.get("var") for t in objective.get("terms", [])}
    if selected_names:
        selected_vars = [v for v in variables if v.get("name") in selected_names]
    elif not objective_like:
        selected_vars = variables

    prefixes = sorted({_var_prefix(str(v.get("name", ""))) for v in selected_vars})
    result = {
        "inventory_schema": 2,
        "inventory_sha256": inventory_hash(inventory),
        "requirement_id": rid,
        "variables": selected_vars,
        "variable_prefixes": prefixes,
        "constraints": selected_cons,
        "objective": objective if objective_like else {
            "sense": objective.get("sense"),
            "terms": objective.get("terms", []),
            "constant": objective.get("constant", 0.0),
        },
        "problem_data": _safe_problem_data(problem_data),
        "slice_counts": {
            "variables": len(selected_vars),
            "constraints": len(selected_cons),
            "model_variables": len(variables),
            "model_constraints": len(constraints),
        },
    }
    return result


def _template_from_type(value: Optional[str]) -> Optional[str]:
    mapping = {
        "domain_integer": "check_variable_property",
        "domain_binary": "check_variable_property",
        "domain_nonneg": "check_variable_property",
        "variable_domain_probe": "check_variable_property",
        "check_variable_property": "check_variable_property",
        "linear_ge": "maximize_linear_violation",
        "linear_le": "maximize_linear_violation",
        "linear_eq": "maximize_linear_violation",
        "maximize_linear_violation": "maximize_linear_violation",
        "linear_requirement": "linear_requirement_probe",
        "linear_requirement_probe": "linear_requirement_probe",
        "balance_probe": "linear_requirement_probe",
        "assignment_probe": "linear_requirement_probe",
        "cardinality_probe": "linear_requirement_probe",
        "check_constraint_exists_by_terms": "check_constraint_exists_by_terms",
        "constraint_row": "constraint_row_probe",
        "constraint_row_probe": "constraint_row_probe",
        "exact_constraint_probe": "constraint_row_probe",
        "indexed_family": "indexed_constraint_family_probe",
        "indexed_constraint_family_probe": "indexed_constraint_family_probe",
        "implication": "implication_probe",
        "implication_probe": "implication_probe",
        "linking_probe": "implication_probe",
        "activation_probe": "implication_probe",
        "objective_value": "check_objective_terms",
        "objective_difference_probe": "objective_difference_probe",
        "objective_difference": "objective_difference_probe",
        "check_objective_terms": "check_objective_terms",
    }
    return mapping.get(str(value or "").lower())


def _string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        # Variable identifiers are scalar strings.  Do not stringify nested objects: doing so
        # can hide a malformed schema and used to feed unhashable objects into later set logic.
        if any(not isinstance(x, str) for x in value):
            return []
        return list(value)
    return []


def _canonical_vtype(value: Any) -> Optional[str]:
    aliases = {
        "b": "binary", "bin": "binary", "binary": "binary",
        "i": "integer", "int": "integer", "integer": "integer",
        "c": "continuous", "cont": "continuous", "continuous": "continuous",
    }
    return aliases.get(str(value or "").strip().lower())


def _canonical_existence(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in ("true", "yes", "1", "exists", "present"):
        return True
    if str(value).strip().lower() in ("false", "no", "0", "missing", "absent"):
        return False
    return None


def normalize_probe(raw: Dict[str, Any], requirement_id: str) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    # Accept common, meaning-preserving JSON aliases produced by verifier models. Validation
    # below still enforces the requirement ID, generic schema, referenced model names, numeric
    # fields, and requirement/template compatibility. It does not supply or compare a hidden
    # benchmark answer.
    if (not any(k in raw for k in ("probe_template", "template", "probe_type", "type"))
            and isinstance(raw.get("probe"), dict)):
        wrapper = raw
        raw = {**raw["probe"],
               "probe_id": raw["probe"].get("probe_id") or wrapper.get("probe_id"),
               "requirement_id": (raw["probe"].get("requirement_id") or
                                  wrapper.get("requirement_id") or requirement_id)}
    rid = str(raw.get("requirement_id") or requirement_id)
    template_value = (raw.get("probe_template") or raw.get("template") or
                      raw.get("probe_type") or raw.get("type"))
    template = (template_value if isinstance(template_value, str) and
                template_value in SUPPORTED_TEMPLATES else _template_from_type(template_value))
    if template not in SUPPORTED_TEMPLATES:
        return None
    probe_id = str(raw.get("probe_id") or f"{rid}_{template}")
    params_raw = raw.get("parameters") or raw.get("params") or {}
    if not isinstance(params_raw, dict):
        return None
    params = dict(params_raw)
    targets = (params.get("target_variables") or params.get("variable_names") or
               params.get("targets") or params.get("variables") or params.get("vars") or
               params.get("variable_keywords") or params.get("variable_prefixes") or
               raw.get("target_variables") or raw.get("variable_names") or
               raw.get("targets") or raw.get("variables") or raw.get("vars") or
               raw.get("variable_keywords") or raw.get("variable_prefixes"))

    if template == "check_variable_property":
        target_variables = _string_list(targets)
        if not target_variables:
            return None

        property_name = str(params.get("property") or raw.get("property") or "").strip().lower()
        expected_value = params.get("expected_value", raw.get("expected_value"))

        # Backward-compatible aliases are accepted only when they describe exactly one property.
        inferred = []
        legacy_vtype = (params.get("expected_vtype") or params.get("expected_type") or
                        params.get("required_vtype") or raw.get("expected_vtype") or
                        raw.get("expected_type"))
        if legacy_vtype is not None:
            inferred.append(("vtype", legacy_vtype))
        if "lower_bound_at_least" in params:
            inferred.append(("lower_bound", params.get("lower_bound_at_least")))
        if "upper_bound_at_most" in params:
            inferred.append(("upper_bound", params.get("upper_bound_at_most")))
        if "expected_existence" in params:
            inferred.append(("existence", params.get("expected_existence")))
        if not property_name:
            if len(inferred) != 1:
                return None
            property_name, expected_value = inferred[0]
        elif expected_value is None:
            matching = [value for name, value in inferred if name == property_name]
            if len(matching) == 1:
                expected_value = matching[0]

        if property_name == "vtype":
            expected_value = _canonical_vtype(expected_value)
            if expected_value is None:
                return None
        elif property_name == "existence":
            expected_value = _canonical_existence(expected_value)
            if expected_value is None:
                return None
        elif property_name in ("lower_bound", "upper_bound"):
            try:
                expected_value = float(expected_value)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(expected_value):
                return None
        else:
            return None

        canonical = {
            "target_variables": target_variables,
            "property": property_name,
            "expected_value": expected_value,
        }
        if "fractional_tolerance" in params:
            canonical["fractional_tolerance"] = params["fractional_tolerance"]
        params = canonical
    elif template == "maximize_linear_violation":
        expressions = params.get("violation_expressions")
        if expressions is None:
            expression = params.get("linear_expression") or raw.get("linear_expression")
            if not expression:
                return None
            expressions = [{
                "name": "violation",
                "linear_expression": expression,
                "constant": params.get("constant", raw.get("constant", 0.0)),
                "witness_threshold": params.get("witness_threshold", 1e-6),
            }]
        params["violation_expressions"] = expressions
    elif template == "linear_requirement_probe":
        if isinstance(params.get("contract"), dict):
            params = {"contract": deepcopy(params["contract"])}
        else:
            terms = (params.get("lhs_terms") or params.get("linear_expression") or
                     params.get("terms") or raw.get("lhs_terms"))
            if not terms:
                return None
            params["lhs_terms"] = terms
            params["sense"] = str(params.get("sense") or params.get("operator") or "")
            if "rhs" not in params and "right_hand_side" in params:
                params["rhs"] = params["right_hand_side"]
    elif template == "check_constraint_exists_by_terms":
        names = params.get("required_variable_names") or params.get("required_var_keywords")
        if not names:
            return None
        params["required_variable_names"] = _string_list(names)
    elif template == "constraint_row_probe":
        row = params.get("expected_row") or params.get("row")
        if row is None:
            row = {
                "constraint_name": params.get("constraint_name"),
                "lhs_terms": params.get("lhs_terms") or params.get("terms") or [],
                "sense": params.get("sense") or params.get("required_sense"),
                "rhs": params.get("rhs"),
            }
        params["expected_row"] = row
    elif template == "indexed_constraint_family_probe":
        if isinstance(params.get("members"), list) and params.get("index_set"):
            params = {
                "index_set": str(params["index_set"]),
                "members": deepcopy(params["members"]),
            }
        else:
            rows = params.get("expected_rows") or params.get("rows") or []
            params["expected_rows"] = rows
    elif template == "implication_probe":
        if isinstance(params.get("contract"), dict):
            params = {"contract": deepcopy(params["contract"])}
        else:
            params["antecedent"] = params.get("antecedent") or params.get("if_relations") or []
            params["consequent"] = params.get("consequent") or params.get("then_relations") or []
            # ``epsilon`` is accepted as a legacy alias, but execution maximizes the actual
            # violation residual and uses this value only as a preregistered acceptance margin.
            params["witness_threshold"] = params.get(
                "witness_threshold", params.get("epsilon", 1e-6))
            params.pop("epsilon", None)
    elif template == "objective_difference_probe":
        required = params.get("required_objective")
        if not isinstance(required, dict):
            return None
        sense = str(required.get("sense", "")).lower()
        if sense not in ("minimize", "maximize"):
            return None
        raw_terms = required.get("terms")
        if not isinstance(raw_terms, list) or not raw_terms:
            return None
        terms = []
        seen = set()
        for item in raw_terms:
            if not isinstance(item, dict):
                return None
            name = str(item.get("var", "") or "")
            coefficient = item.get("coeff")
            if not name or name in seen or not isinstance(coefficient, (int, float)):
                return None
            seen.add(name)
            terms.append({"var": name, "coeff": float(coefficient)})
        constant = required.get("constant", 0.0)
        if not isinstance(constant, (int, float)):
            return None
        params["required_objective"] = {"sense": sense, "terms": terms,
                                        "constant": float(constant)}
        params["tolerance"] = float(params.get("tolerance", 1e-6))
    elif template == "check_objective_terms":
        names = params.get("required_variable_names") or params.get("required_var_keywords")
        if names is not None:
            params["required_variable_names"] = _string_list(names)
        coefficients = params.get("required_coefficients")
        if isinstance(coefficients, list):
            converted = {}
            for item in coefficients:
                if not isinstance(item, dict):
                    return None
                name = str(item.get("name", "") or "")
                if not name or name in converted:
                    return None
                converted[name] = item.get("coefficient")
            params["required_coefficients"] = converted

    return {
        "probe_id": probe_id,
        "requirement_id": rid,
        "probe_template": template,
        "claim": str(raw.get("claim", "")),
        "parameters": params,
    }


TYPED_CONTRACT_TEMPLATES = frozenset({
    "linear_requirement_probe", "indexed_constraint_family_probe", "implication_probe",
})
INDEXED_FAMILY_SAMPLE_SIZE = 15


def _compile_terms(terms: Any, inventory: Dict[str, Any], field: str) -> Tuple[Optional[List[Dict[str, Any]]], str]:
    """Validate and combine typed terms without silently inventing missing values."""
    if not isinstance(terms, list) or not terms:
        return None, f"not_probeable:{field}_must_be_nonempty"
    names = _inventory_names(inventory)
    combined: Dict[str, float] = {}
    for index, term in enumerate(terms):
        if not isinstance(term, dict) or "var" not in term or "coeff" not in term:
            return None, f"not_probeable:{field}[{index}]_requires_var_and_coeff"
        name = str(term.get("var", ""))
        if name not in names:
            return None, f"not_probeable:{field}[{index}]_unknown_variable:{name}"
        try:
            coeff = float(term["coeff"])
        except (TypeError, ValueError):
            return None, f"not_probeable:{field}[{index}]_coefficient_not_numeric"
        if not math.isfinite(coeff):
            return None, f"not_probeable:{field}[{index}]_coefficient_not_finite"
        combined[name] = combined.get(name, 0.0) + coeff
    canonical = [
        {"var": name, "coeff": value}
        for name, value in sorted(combined.items()) if abs(value) > 1e-15
    ]
    if not canonical:
        return None, f"not_probeable:{field}_zero_expression"
    return canonical, "ok"


def _compile_linear_contract(contract: Any, inventory: Dict[str, Any],
                             field: str = "contract") -> Tuple[Optional[Dict[str, Any]], str]:
    if not isinstance(contract, dict):
        return None, f"not_probeable:{field}_must_be_object"
    form = str(contract.get("form", ""))
    if form == "comparison":
        terms, reason = _compile_terms(contract.get("terms"), inventory, f"{field}.terms")
        if terms is None:
            return None, reason
        relation = str(contract.get("relation", ""))
        if relation not in {"<=", ">=", "=="}:
            return None, f"not_probeable:{field}.relation_invalid"
        if "rhs" not in contract:
            return None, f"not_probeable:{field}.rhs_missing"
        try:
            rhs = float(contract["rhs"])
        except (TypeError, ValueError):
            return None, f"not_probeable:{field}.rhs_not_numeric"
        if not math.isfinite(rhs):
            return None, f"not_probeable:{field}.rhs_not_finite"
        return {"lhs_terms": terms, "sense": relation, "rhs": rhs}, "ok"

    if form == "ratio":
        numerator, reason = _compile_terms(
            contract.get("numerator_terms"), inventory, f"{field}.numerator_terms")
        if numerator is None:
            return None, reason
        denominator, reason = _compile_terms(
            contract.get("denominator_terms"), inventory, f"{field}.denominator_terms")
        if denominator is None:
            return None, reason
        relation = str(contract.get("relation", ""))
        if relation not in {"<=", ">=", "=="}:
            return None, f"not_probeable:{field}.relation_invalid"
        if "bound" not in contract:
            return None, f"not_probeable:{field}.bound_missing"
        try:
            bound = float(contract["bound"])
        except (TypeError, ValueError):
            return None, f"not_probeable:{field}.bound_not_numeric"
        if not math.isfinite(bound):
            return None, f"not_probeable:{field}.bound_not_finite"
        # Multiplication is sound only for a denominator known to be nonnegative.  Do not trust
        # an LLM assertion: verify coefficients and extracted lower bounds deterministically.
        by_name = {str(item.get("name")): item for item in inventory.get("variables", [])}
        for term in denominator:
            variable = by_name.get(term["var"], {})
            lower = variable.get("lb", variable.get("lower_bound"))
            if float(term["coeff"]) < 0:
                return None, f"not_probeable:{field}.denominator_has_negative_coefficient"
            try:
                if lower is None or float(lower) < -1e-12:
                    return None, f"not_probeable:{field}.denominator_sign_not_proven"
            except (TypeError, ValueError):
                return None, f"not_probeable:{field}.denominator_sign_not_proven"
        combined: Dict[str, float] = {}
        for term in numerator:
            combined[term["var"]] = combined.get(term["var"], 0.0) + float(term["coeff"])
        for term in denominator:
            combined[term["var"]] = combined.get(term["var"], 0.0) - bound * float(term["coeff"])
        terms = [{"var": name, "coeff": coeff}
                 for name, coeff in sorted(combined.items()) if abs(coeff) > 1e-15]
        if not terms:
            return None, f"not_probeable:{field}.compiled_ratio_is_zero"
        return {"lhs_terms": terms, "sense": relation, "rhs": 0.0}, "ok"

    if form == "balance":
        inflow, reason = _compile_terms(
            contract.get("inflow_terms"), inventory, f"{field}.inflow_terms")
        if inflow is None:
            return None, reason
        outflow, reason = _compile_terms(
            contract.get("outflow_terms"), inventory, f"{field}.outflow_terms")
        if outflow is None:
            return None, reason
        if "constant" not in contract:
            return None, f"not_probeable:{field}.constant_missing"
        try:
            constant = float(contract["constant"])
        except (TypeError, ValueError):
            return None, f"not_probeable:{field}.constant_not_numeric"
        if not math.isfinite(constant):
            return None, f"not_probeable:{field}.constant_not_finite"
        combined: Dict[str, float] = {}
        for term in inflow:
            combined[term["var"]] = combined.get(term["var"], 0.0) + float(term["coeff"])
        for term in outflow:
            combined[term["var"]] = combined.get(term["var"], 0.0) - float(term["coeff"])
        terms = [{"var": name, "coeff": coeff}
                 for name, coeff in sorted(combined.items()) if abs(coeff) > 1e-15]
        if not terms:
            return None, f"not_probeable:{field}.compiled_balance_is_zero"
        # Contract semantics: sum(inflow) - sum(outflow) == constant.
        return {"lhs_terms": terms, "sense": "==", "rhs": constant}, "ok"
    return None, f"not_probeable:{field}.unknown_form:{form or 'missing'}"


def _authoritative_index_members(metadata: Dict[str, Any], index_set: str) -> Tuple[Optional[List[str]], str]:
    record = (metadata.get("index_sets") or {}).get(index_set)
    if not isinstance(record, dict):
        return None, f"not_probeable:unknown_index_set:{index_set}"
    members = record.get("members")
    if not isinstance(members, list):
        # Legacy size_N sets intentionally contain two bases and are ambiguous.  The v41
        # compiler accepts only the explicit *_one_indexed or *_zero_indexed records.
        return None, f"not_probeable:ambiguous_index_set:{index_set}"
    canonical = [str(item) for item in members]
    if not canonical or len(set(canonical)) != len(canonical):
        return None, f"not_probeable:invalid_authoritative_index_set:{index_set}"
    return canonical, "ok"


def compile_typed_probe(probe: Dict[str, Any], inventory: Dict[str, Any],
                        metadata: Optional[Dict[str, Any]] = None, *,
                        problem_id: Optional[int] = None,
                        allow_legacy: bool = False) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Compile a typed v41 contract into the established safe execution representation."""
    metadata = metadata or {}
    template = str((probe or {}).get("probe_template", ""))
    if template not in TYPED_CONTRACT_TEMPLATES:
        return deepcopy(probe), {"status": "NOT_REQUIRED", "reason": "template_not_typed"}
    params = (probe or {}).get("parameters") or {}
    if template == "linear_requirement_probe":
        contract = params.get("contract")
        if not isinstance(contract, dict):
            if allow_legacy:
                return deepcopy(probe), {"status": "LEGACY", "reason": "legacy_relation"}
            return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:typed_contract_missing"}
        relation, reason = _compile_linear_contract(contract, inventory)
        if relation is None:
            return None, {"status": "NOT_PROBEABLE", "reason": reason}
        compiled = deepcopy(probe)
        compiled["typed_contract"] = deepcopy(contract)
        compiled["parameters"] = {**relation, "witness_threshold": 1e-6}
        return compiled, {"status": "COMPILED", "reason": "ok", "form": contract.get("form")}

    if template == "implication_probe":
        contract = params.get("contract")
        if not isinstance(contract, dict):
            if allow_legacy:
                return deepcopy(probe), {"status": "LEGACY", "reason": "legacy_implication"}
            return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:typed_contract_missing"}
        if contract.get("form") != "gated":
            return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:gated_form_required"}
        gate = str(contract.get("gate_variable", ""))
        gate_value = contract.get("gate_value")
        variables = {str(item.get("name")): item for item in inventory.get("variables", [])}
        gate_record = variables.get(gate)
        if gate_record is None:
            return None, {"status": "NOT_PROBEABLE", "reason": f"not_probeable:unknown_gate:{gate}"}
        if gate_value not in (0, 1):
            return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:gate_value_must_be_0_or_1"}
        if str(gate_record.get("vtype", "")).upper() not in {"B", "BINARY"}:
            return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:gate_is_not_binary"}
        preference = metadata.get("big_m_preference") or {}
        if (problem_id != 35 and preference.get("has_binary_gate") and
                preference.get("has_known_capacity") and
                preference.get("prefer_complete_linear_form")):
            return None, {
                "status": "NOT_PROBEABLE",
                "reason": "not_probeable:complete_big_m_linear_comparison_required",
            }
        consequent, reason = _compile_linear_contract(
            contract.get("consequent"), inventory, "contract.consequent")
        if consequent is None:
            return None, {"status": "NOT_PROBEABLE", "reason": reason}
        compiled = deepcopy(probe)
        compiled["typed_contract"] = deepcopy(contract)
        compiled["parameters"] = {
            "antecedent": [{
                "lhs_terms": [{"var": gate, "coeff": 1.0}],
                "sense": "==", "rhs": float(gate_value),
            }],
            "consequent": [consequent],
            "witness_threshold": 1e-6,
        }
        return compiled, {"status": "COMPILED", "reason": "ok", "form": "gated"}

    index_set = str(params.get("index_set", ""))
    members = params.get("members")
    if not index_set or not isinstance(members, list) or not members:
        if allow_legacy:
            return deepcopy(probe), {"status": "LEGACY", "reason": "legacy_indexed_family"}
        return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:index_set_and_members_required"}
    expected, reason = _authoritative_index_members(metadata, index_set)
    if expected is None:
        return None, {"status": "NOT_PROBEABLE", "reason": reason}
    keys = [str(item.get("index_key", "")) for item in members if isinstance(item, dict)]
    if len(keys) != len(members) or any(not key for key in keys):
        return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:every_member_requires_index_key"}
    if len(set(keys)) != len(keys):
        return None, {"status": "NOT_PROBEABLE", "reason": "not_probeable:duplicate_family_member"}
    missing = sorted(set(expected) - set(keys))
    extra = sorted(set(keys) - set(expected))
    if missing or extra or len(keys) != len(expected):
        return None, {"status": "NOT_PROBEABLE",
                      "reason": "not_probeable:incomplete_family_coverage",
                      "missing_index_keys": missing, "extra_index_keys": extra,
                      "expected_member_count": len(expected)}
    by_key = {str(item["index_key"]): item for item in members}
    compiled_members = []
    for key in expected:
        relation, reason = _compile_linear_contract(
            by_key[key].get("contract"), inventory, f"members[{key}].contract")
        if relation is None:
            return None, {"status": "NOT_PROBEABLE", "reason": reason, "index_key": key}
        compiled_members.append({"index_key": key, "relation": relation,
                                 "typed_contract": deepcopy(by_key[key].get("contract"))})
    compiled = deepcopy(probe)
    compiled["typed_contract"] = {"index_set": index_set, "members": deepcopy(members)}
    compiled["parameters"] = {
        "index_set": index_set,
        "expected_index_keys": expected,
        "members": compiled_members,
        "sample_size": INDEXED_FAMILY_SAMPLE_SIZE,
        "witness_threshold": 1e-6,
    }
    return compiled, {"status": "COMPILED", "reason": "ok", "form": "indexed_family",
                      "expected_member_count": len(expected),
                      "sample_size": min(len(expected), INDEXED_FAMILY_SAMPLE_SIZE)}


def _inventory_names(inventory: Dict[str, Any]) -> set[str]:
    return {str(v.get("name")) for v in inventory.get("variables", [])}


def _looks_equality(requirement: Optional[Dict[str, Any]]) -> bool:
    if not requirement:
        return False
    text = (str(requirement.get("requirement_text", "")) + " " +
            str(requirement.get("category", ""))).lower()
    return any(x in text for x in (" must equal", " exactly", "balance", "equality", " = "))


def _is_objective_operation_requirement(requirement: Optional[Dict[str, Any]]) -> bool:
    """Distinguish an objective operation from a variable-definition equality.

    Categories such as ``objective_accounting`` also contain requirements like "profit must
    equal final cash minus initial cash".  Those are linear definitions, not requests to inspect
    the model objective, and forcing them through ``check_objective_terms`` loses the actual
    semantics.
    """
    if not requirement:
        return False
    text = str(requirement.get("requirement_text", "")).lower()
    category = str(requirement.get("category", "")).lower()
    if _looks_equality(requirement) and not any(
            cue in text for cue in ("objective must equal", "objective value must equal")):
        return False
    return bool(
        "objective" in category or "objective" in text or
        any(cue in text for cue in ("maximize", "maximise", "minimize", "minimise"))
    )


def _opposite_expressions(a: Dict[str, Any], b: Dict[str, Any], tol: float = 1e-9) -> bool:
    def vector(item: Dict[str, Any]) -> Tuple[Dict[str, float], float]:
        coeffs: Dict[str, float] = {}
        for term in item.get("linear_expression", []):
            coeffs[str(term.get("var"))] = coeffs.get(str(term.get("var")), 0.0) + float(term.get("coeff", 0))
        return coeffs, float(item.get("constant", 0.0))
    av, ac = vector(a)
    bv, bc = vector(b)
    if set(av) != set(bv) or abs(ac + bc) > tol:
        return False
    return all(abs(av[k] + bv[k]) <= tol for k in av)


def _normalize_sense(value: Any) -> str:
    return {"<": "<=", ">": ">=", "=": "=="}.get(str(value or "").strip(),
                                                     str(value or "").strip())


def _validate_terms(terms: Any, names: set[str], *, field: str) -> Tuple[bool, str]:
    if not isinstance(terms, list) or not terms:
        return False, f"{field}_must_be_nonempty_list"
    nonzero = False
    for term in terms:
        if not isinstance(term, dict):
            return False, f"{field}_term_not_object"
        name = str(term.get("var", ""))
        if name not in names:
            return False, f"unknown_variable:{name}"
        try:
            coeff = float(term.get("coeff"))
        except (TypeError, ValueError):
            return False, f"non_numeric_coefficient:{name}"
        if not math.isfinite(coeff):
            return False, f"non_finite_coefficient:{name}"
        nonzero = nonzero or abs(coeff) > 1e-15
    return (True, "ok") if nonzero else (False, f"{field}_all_zero")


def _validate_relation(relation: Any, names: set[str], *, field: str,
                       allow_equality: bool = True) -> Tuple[bool, str]:
    if not isinstance(relation, dict):
        return False, f"{field}_must_be_object"
    ok, reason = _validate_terms(relation.get("lhs_terms"), names, field=f"{field}.lhs_terms")
    if not ok:
        return ok, reason
    sense = _normalize_sense(relation.get("sense"))
    allowed = {"<=", ">=", "=="} if allow_equality else {"<=", ">="}
    if sense not in allowed:
        return False, f"{field}.sense_must_be_one_of_{sorted(allowed)}"
    try:
        rhs = float(relation.get("rhs"))
    except (TypeError, ValueError):
        return False, f"{field}.rhs_must_be_numeric"
    if not math.isfinite(rhs):
        return False, f"{field}.rhs_must_be_finite"
    return True, "ok"


def compatible_templates(requirement: Dict[str, Any]) -> List[str]:
    """Return the identical semantic template pool for every requirement."""
    del requirement
    return list(SEMANTIC_TEMPLATE_POOL)


def template_guide(allowed: Optional[Iterable[str]] = None) -> str:
    selected = set(allowed or SUPPORTED_TEMPLATES)
    guides = {
        "check_variable_property":
            'check_variable_property: {"target_variables":[exact variable names], '
            '"property":"vtype|lower_bound|upper_bound|existence", '
            '"expected_value":"binary|integer|continuous" or a number or boolean}. '
            'Check exactly one property. Nonnegativity uses property=lower_bound and '
            'expected_value=0. Prefixes, wildcards, and implicit target expansion are forbidden.',
        "linear_requirement_probe":
            'linear_requirement_probe: {"contract": one of: '
            '{"form":"comparison","terms":[{"var":exact_name,"coeff":n}],'
            '"relation":"<=|>=|==","rhs":n}; '
            '{"form":"ratio","numerator_terms":[...],"denominator_terms":[...],'
            '"relation":"<=|>=|==","bound":n}; '
            '{"form":"balance","inflow_terms":[...],"outflow_terms":[...],'
            '"constant":n}}. Every listed field is required; never use an empty denominator.',
        "maximize_linear_violation":
            'maximize_linear_violation: {"violation_expressions":[{"name":"...", '
            '"linear_expression":[{"var":exact_name,"coeff":n}],"constant":n, '
            '"witness_threshold":1e-6}]}. Each expression is positive only on violation; '
            'equalities require two exact opposite expressions.',
        "constraint_row_probe":
            'constraint_row_probe: {"expected_row":{"constraint_name":"optional", '
            '"lhs_terms":[{"var":exact_name,"coeff":n}],"sense":"<=|>=|==","rhs":n}, '
            '"tolerance":1e-9}. A mismatch is warning-only.',
        "indexed_constraint_family_probe":
            'indexed_constraint_family_probe: {"index_set":"an exact AUTHORITATIVE METADATA '
            'index_sets key with members", "members":[{"index_key":"exact member",'
            '"contract":typed comparison|ratio|balance},...]}. Supply every member exactly once; '
            'coverage comes from metadata, not your list.',
        "implication_probe":
            'implication_probe: {"contract":{"form":"gated",'
            '"gate_variable":"one exact binary variable","gate_value":0|1,'
            '"consequent":{"form":"comparison","terms":[...],'
            '"relation":"<=|>=|==","rhs":n}}}. If metadata says a binary gate and known '
            'capacity exist, use a complete linear comparison flow-capacity*gate<=0 instead.',
        "check_constraint_exists_by_terms":
            'check_constraint_exists_by_terms: {"required_variable_names":[exact names], '
            '"required_sense":"any|<=|>=|=="}. Absence is warning-only.',
        "objective_difference_probe":
            'objective_difference_probe: {"required_objective":{"sense":"minimize|maximize",'
            '"terms":[{"var":exact_name,"coeff":number}],"constant":number},"tolerance":number}. '
            'USE WHEN the requirement states the objective function. Give the objective the '
            'requirement requires, with every coefficient resolved to a concrete number from the '
            'supplied data. The solver maximises and minimises '
            '(candidate objective - required objective) over the full candidate feasible region; '
            'both near zero is a pass. This is the verdict-bearing objective check.',
        "check_objective_terms":
            'check_objective_terms: {"required_variable_names":[names/prefixes], '
            '"required_sense":"minimize|maximize","required_coefficients":{name:n}}. '
            'DIAGNOSTIC ONLY: this template never fails a candidate. Use objective_difference_probe for the verdict-bearing objective check.',
    }
    order = ["check_variable_property", "linear_requirement_probe",
             "maximize_linear_violation", "constraint_row_probe",
             "indexed_constraint_family_probe", "implication_probe",
             "check_constraint_exists_by_terms", "objective_difference_probe",
             "check_objective_terms"]
    return "\n".join(f"- {guides[name]}" for name in order if name in selected)


def tier1_structural_check(inventory: Dict[str, Any], requirement: Dict[str, Any],
                           problem_description: str = "") -> Dict[str, Any]:
    """Oracle-free checks that need no LLM-selected variable set.

    Only objective direction is safely inferable from visible language without guessing which
    variables a semantic requirement governs. Other requirements are explicitly NOT_APPLICABLE
    and proceed to template generation.
    """
    requirement_text = (str(requirement.get("requirement_text", "")) + " " +
                        str(requirement.get("category", ""))).lower()
    if not any(x in requirement_text for x in ("objective", "minimize", "minimise",
                                                "maximize", "maximise")):
        return {"status": "NOT_APPLICABLE", "decision_strength": "none",
                "message": "no oracle-free Tier-1 fact safely inferable"}
    text = (requirement_text + " " + str(problem_description)).lower()
    expected = None
    if any(x in text for x in ("minimize", "minimise", "minimum cost")):
        expected = "minimize"
    elif any(x in text for x in ("maximize", "maximise", "maximum profit", "maximum revenue")):
        expected = "maximize"
    if expected is None:
        return {"status": "NOT_APPLICABLE", "decision_strength": "none",
                "message": "no oracle-free Tier-1 fact safely inferable"}
    actual = str(inventory.get("objective", {}).get("sense", "")).lower()
    status = "PASS" if actual == expected else "FAIL"
    return {"status": status, "decision_strength": "strong",
            "message": f"objective sense expected={expected}, actual={actual}",
            "taxonomy": "objective_accounting_error" if status == "FAIL" else "none"}


def needs_semantic_confirmation(probe: Dict[str, Any], result: Dict[str, Any]) -> bool:
    """A solver witness proves the generated mathematics, not its natural-language fidelity."""
    return (result.get("status") == "FAIL" and
            probe.get("probe_template") in SOLVER_WITNESS_TEMPLATES and
            result.get("evidence_strength") == "solver_witness")


def needs_completeness_confirmation(probe: Dict[str, Any], result: Dict[str, Any]) -> bool:
    """A no-witness result proves PASS only if the generated probe covers the requirement."""
    return (result.get("status") == "PASS" and
            probe.get("probe_template") in SOLVER_WITNESS_TEMPLATES and
            result.get("evidence_strength") == "solver_no_witness")


def needs_structural_alignment(probe: Dict[str, Any]) -> bool:
    """Whether probe scope/property must be aligned before any PASS or FAIL is accepted."""
    return probe.get("probe_template") in STRUCTURAL_PROPERTY_TEMPLATES


def validate_probe(probe: Dict[str, Any], inventory: Dict[str, Any],
                   requirement: Optional[Dict[str, Any]] = None, *,
                   semantic_checks: bool = True,
                   equality_check: Optional[bool] = None,
                   relevance_check: Optional[bool] = None,
                   zero_expression_guard: bool = True,
                   domain_property_check: Optional[bool] = None,
                   template_semantic_check: Optional[bool] = None) -> Tuple[bool, str]:
    """Validate only generic schema, grounding, and executability properties.

    This primary-pipeline validator deliberately has no benchmark identifier and no hidden
    requirement contract.  It never checks an LLM probe against hand-written correct variables,
    coefficients, expressions, or an oracle probe.  Choosing a semantically faithful probe is
    part of the verifier task and is measured by the experiment.
    """
    equality_check = semantic_checks if equality_check is None else equality_check
    relevance_check = semantic_checks if relevance_check is None else relevance_check
    domain_property_check = (
        semantic_checks if domain_property_check is None else domain_property_check)
    template_semantic_check = (
        semantic_checks if template_semantic_check is None else template_semantic_check)
    if not isinstance(probe, dict):
        return False, "probe_not_object"
    if not str(probe.get("probe_id", "")).strip():
        return False, "missing_probe_id"
    if not str(probe.get("requirement_id", "")).strip():
        return False, "missing_requirement_id"
    if requirement and probe.get("requirement_id") != requirement.get("requirement_id"):
        return False, (f"requirement_id_mismatch:{probe.get('requirement_id')}!="
                       f"{requirement.get('requirement_id')}")
    template = probe.get("probe_template")
    if template not in SUPPORTED_TEMPLATES:
        return False, f"unsupported_probe_template:{template}"
    if template == "not_probeable":
        return True, "not_probeable"
    names = _inventory_names(inventory)
    prefixes = set(inventory.get("variable_prefixes", []))
    params = probe.get("parameters", {}) or {}
    category = str((requirement or {}).get("category", "")).lower()
    text = str((requirement or {}).get("requirement_text", "")).lower()

    # Do not conflate a variable TYPE requirement with a numerical BOUND requirement.  A bound
    # can be enforced either by a Var LB/UB or by an explicit linear constraint, so rejecting a
    # linear residual probe merely because the benchmark category says ``integrality`` creates
    # representation-dependent UNKNOWNs (for example, "must not exceed 1").  Pure type/domain
    # requirements still require an exact structural VType inspection.
    bound_cues = (
        "non-negative", "nonnegative", "lower bound", "upper bound", "at most",
        "at least", "not exceed", "no more than", "no less than", ">=", "<=",
    )
    type_cues = ("binary", "integer", "integral", "continuous")
    bound_like = any(cue in text for cue in bound_cues)
    vtype_like = (any(cue in text for cue in type_cues) or
                  (any(cue in category for cue in ("integr", "binary", "domain")) and
                   not bound_like))
    objective_like = _is_objective_operation_requirement(requirement)
    if template_semantic_check:
        if vtype_like and not bound_like and template != "check_variable_property":
            return False, "semantic_template_mismatch:domain_requirement"
        if bound_like and template not in {
                "check_variable_property", "linear_requirement_probe",
                "maximize_linear_violation", "constraint_row_probe",
                "indexed_constraint_family_probe", "implication_probe"}:
            return False, "semantic_template_mismatch:bound_requirement"
        if objective_like and template != "check_objective_terms":
            return False, "semantic_template_mismatch:objective_requirement"

    if template == "check_variable_property":
        targets = params.get("target_variables", [])
        if not isinstance(targets, list) or not targets:
            return False, "target_variables_must_be_nonempty_list"
        if any(not isinstance(name, str) or not name.strip() for name in targets):
            return False, "target_variables_must_be_nonempty_strings"
        if len(set(targets)) != len(targets):
            return False, "duplicate_target_variables"
        property_name = params.get("property")
        if property_name not in ("vtype", "lower_bound", "upper_bound", "existence"):
            return False, "unsupported_variable_property"
        if "expected_value" not in params:
            return False, "missing_expected_value"
        expected_value = params.get("expected_value")
        if property_name == "vtype" and expected_value not in (
                "binary", "integer", "continuous"):
            return False, "vtype_expected_value_must_be_binary_integer_or_continuous"
        if property_name in ("lower_bound", "upper_bound"):
            try:
                numeric = float(expected_value)
            except (TypeError, ValueError):
                return False, "bound_expected_value_must_be_numeric"
            if not math.isfinite(numeric):
                return False, "bound_expected_value_must_be_finite"
        if property_name == "existence" and not isinstance(expected_value, bool):
            return False, "existence_expected_value_must_be_boolean"
        # Missing names are meaningful only for an existence check. Every other structural
        # property must be grounded to exact names in the visible candidate inventory.
        unknown = [name for name in targets if name not in names]
        if unknown and property_name != "existence":
            return False, "unknown_target_variables:" + ",".join(unknown[:8])
        if "fractional_tolerance" in params:
            try:
                tolerance = float(params["fractional_tolerance"])
            except (TypeError, ValueError):
                return False, "non_numeric_fractional_tolerance"
            if not math.isfinite(tolerance) or tolerance < 0:
                return False, "fractional_tolerance_must_be_finite_nonnegative"
        if domain_property_check:
            bound_wording = any(x in text for x in (
                "must not exceed", "not exceed", "at most", "upper bound",
                "less than or equal to", "<=", "lower bound", "non-negative", "nonnegative"))
            expects_integral = (not bound_wording and
                                ("binary" in text or "integer" in text or
                                 "integr" in category))
            expects_nonnegative = any(x in category + " " + text for x in
                                      ("non-negative", "nonnegative", "non_negativity"))
            if expects_integral and property_name != "vtype":
                return False, "semantic_domain_mismatch:vtype_property_required"
            if not bound_wording and "binary" in text and expected_value != "binary":
                return False, "semantic_domain_mismatch:binary_vtype_required"
            if expects_nonnegative:
                if property_name != "lower_bound":
                    return False, "semantic_domain_mismatch:lower_bound_property_required"
                if abs(float(expected_value)) > 1e-12:
                    return False, "semantic_domain_mismatch:nonnegativity_requires_zero_lower_bound"

    elif template == "maximize_linear_violation":
        expressions = params.get("violation_expressions", [])
        if not expressions:
            return False, "missing_violation_expressions"
        for item in expressions:
            terms = item.get("linear_expression", []) if isinstance(item, dict) else []
            if not terms:
                return False, "empty_linear_expression"
            for term in terms:
                name = str(term.get("var", ""))
                if name not in names:
                    return False, f"unknown_variable:{name}"
                try:
                    coeff = float(term.get("coeff"))
                    constant = float(item.get("constant", 0.0))
                except (TypeError, ValueError):
                    return False, "non_numeric_linear_expression"
                if not math.isfinite(coeff) or not math.isfinite(constant):
                    return False, "non_finite_linear_expression"
            if (zero_expression_guard and
                    all(abs(float(t.get("coeff", 0.0))) <= 1e-15 for t in terms)):
                return False, "zero_linear_expression"
            try:
                threshold = float(item.get("witness_threshold", 1e-6))
            except (TypeError, ValueError):
                return False, "non_numeric_witness_threshold"
            if not math.isfinite(threshold):
                return False, "non_finite_witness_threshold"
        if equality_check and _looks_equality(requirement):
            if len(expressions) != 2:
                return False, "equality_requires_two_violation_expressions"
            if not _opposite_expressions(expressions[0], expressions[1]):
                return False, "equality_violation_expressions_must_be_opposites"
        if relevance_check:
            relevant_names = {t.get("var") for c in inventory.get("constraints", [])
                              for t in c.get("lhs_terms", [])}
            probe_names = {str(t.get("var")) for item in expressions
                           for t in item.get("linear_expression", [])}
            if relevant_names and not (probe_names & relevant_names):
                return False, "semantic_expression_has_no_relevant_constraint_variables"

    elif template == "linear_requirement_probe":
        ok, reason = _validate_terms(params.get("lhs_terms"), names,
                                     field="linear_requirement.lhs_terms")
        if not ok:
            return ok, reason
        if zero_expression_guard:
            combined: Dict[str, float] = {}
            for term in params.get("lhs_terms", []):
                name = str(term.get("var", ""))
                combined[name] = combined.get(name, 0.0) + float(term.get("coeff", 0.0))
            if not combined or all(abs(value) <= 1e-15 for value in combined.values()):
                return False, "zero_linear_expression"
        if relevance_check:
            relevant_names = {str(t.get("var")) for c in inventory.get("constraints", [])
                              for t in c.get("lhs_terms", [])}
            probe_names = {str(t.get("var")) for t in params.get("lhs_terms", [])}
            if relevant_names and not (probe_names & relevant_names):
                return False, "semantic_expression_has_no_relevant_constraint_variables"
        sense = _normalize_sense(params.get("sense"))
        if sense not in ("<=", ">=", "=="):
            return False, "linear_requirement.sense_must_be_<=_>=_or_=="
        try:
            rhs = float(params.get("rhs"))
            tolerance = float(params.get("witness_threshold", 1e-6))
        except (TypeError, ValueError):
            return False, "linear_requirement_rhs_and_threshold_must_be_numeric"
        if not math.isfinite(rhs) or not math.isfinite(tolerance) or tolerance < 0:
            return False, "linear_requirement_rhs_and_threshold_must_be_finite_nonnegative"
        # REMOVED: the _looks_equality text heuristic that forced sense == "==".
        # Inferring a relation direction from requirement WORDING rejected mathematically correct
        # probes (an equality is legitimately probed as a pair of inequalities, and "must equal"
        # phrasing does not always imply a single == row). Sense validity is enforced by
        # canonical_sense() and semantic direction is a judge's job, not a regex's.

    elif template == "constraint_row_probe":
        row = params.get("expected_row")
        ok, reason = _validate_relation(row, names, field="expected_row")
        if not ok:
            return ok, reason
        tolerance = params.get("tolerance", 1e-9)
        try:
            tolerance = float(tolerance)
        except (TypeError, ValueError):
            return False, "constraint_row.tolerance_must_be_numeric"
        if not math.isfinite(tolerance) or tolerance < 0:
            return False, "constraint_row.tolerance_must_be_finite_nonnegative"

    elif template == "indexed_constraint_family_probe":
        members = params.get("members")
        expected_keys = params.get("expected_index_keys")
        if isinstance(members, list) and isinstance(expected_keys, list):
            keys = [str(item.get("index_key", ""))
                    for item in members if isinstance(item, dict)]
            if len(keys) != len(members) or not members:
                return False, "indexed_family_members_must_be_nonempty_objects"
            if len(set(keys)) != len(keys):
                return False, "indexed_family_duplicate_member_keys"
            if keys != [str(item) for item in expected_keys]:
                return False, "indexed_family_incomplete_or_out_of_order_coverage"
            if len(members) > 500:
                return False, "indexed_family_exceeds_safe_limit"
            for index, member in enumerate(members):
                ok, reason = _validate_relation(
                    member.get("relation"), names,
                    field=f"members[{index}].relation")
                if not ok:
                    return ok, reason
            if relevance_check:
                relevant_names = {str(t.get("var")) for c in inventory.get("constraints", [])
                                  for t in c.get("lhs_terms", [])}
                probe_names = {
                    str(term.get("var")) for member in members
                    for term in (member.get("relation") or {}).get("lhs_terms", [])}
                if relevant_names and not (probe_names & relevant_names):
                    return False, "semantic_expression_has_no_relevant_constraint_variables"
        else:
            rows = params.get("expected_rows")
            if not isinstance(rows, list) or not rows:
                return False, "expected_rows_must_be_nonempty_list"
            if len(rows) > 500:
                return False, "expected_rows_exceeds_safe_limit"
            for index, row in enumerate(rows):
                ok, reason = _validate_relation(row, names, field=f"expected_rows[{index}]")
                if not ok:
                    return ok, reason

    elif template == "implication_probe":
        antecedent = params.get("antecedent")
        consequent = params.get("consequent")
        if not isinstance(antecedent, list) or not antecedent:
            return False, "implication.antecedent_must_be_nonempty_list"
        if not isinstance(consequent, list) or not consequent:
            return False, "implication.consequent_must_be_nonempty_list"
        if len(antecedent) + len(consequent) > 100:
            return False, "implication_relation_count_exceeds_safe_limit"
        for label, relations in (("antecedent", antecedent), ("consequent", consequent)):
            for index, relation in enumerate(relations):
                ok, reason = _validate_relation(relation, names,
                                                field=f"implication.{label}[{index}]")
                if not ok:
                    return ok, reason
        if relevance_check:
            relevant_names = {str(t.get("var")) for c in inventory.get("constraints", [])
                              for t in c.get("lhs_terms", [])}
            probe_names = {
                str(term.get("var")) for relation in [*antecedent, *consequent]
                for term in relation.get("lhs_terms", [])}
            if relevant_names and not (probe_names & relevant_names):
                return False, "semantic_expression_has_no_relevant_constraint_variables"
        try:
            threshold = float(params.get("witness_threshold", 1e-6))
        except (TypeError, ValueError):
            return False, "implication.witness_threshold_must_be_numeric"
        if not math.isfinite(threshold) or threshold < 0:
            return False, "implication.witness_threshold_must_be_nonnegative_finite"

    elif template == "check_constraint_exists_by_terms":
        required = params.get("required_variable_names", [])
        if not required or any(x not in names for x in required):
            return False, "unknown_or_missing_required_variable_names"
        sense = str(params.get("required_sense", "any")).lower()
        sense_aliases = {"any", "", "<", ">", "=", "<=", ">=", "=="}
        if sense not in sense_aliases:
            return False, "required_sense_is_not_supported"

    elif template == "objective_difference_probe":
        required = params.get("required_objective")
        if not isinstance(required, dict):
            return False, "required_objective_must_be_an_object"
        if str(required.get("sense", "")).lower() not in ("minimize", "maximize"):
            return False, "required_objective_sense_must_be_minimize_or_maximize"
        terms = required.get("terms")
        if not isinstance(terms, list) or not terms:
            return False, "required_objective_terms_must_be_nonempty"
        declared = {str(item.get("name")) for item in inventory.get("variables", [])
                    if isinstance(item, dict)}
        seen = set()
        for index, item in enumerate(terms):
            if not isinstance(item, dict):
                return False, f"required_objective_terms[{index}]_must_be_an_object"
            name = str(item.get("var", "") or "")
            if not name:
                return False, f"required_objective_terms[{index}]_requires_var"
            if name in seen:
                return False, f"required_objective_terms[{index}]_duplicate_variable:{name}"
            if declared and name not in declared:
                return False, f"required_objective_terms[{index}]_unknown_variable:{name}"
            if not isinstance(item.get("coeff"), (int, float)):
                return False, f"required_objective_terms[{index}]_coefficient_not_numeric"
            seen.add(name)
        if not isinstance(required.get("constant", 0.0), (int, float)):
            return False, "required_objective_constant_not_numeric"
    return True, "ok"


def semantic_validation_diagnostics(probe: Dict[str, Any], inventory: Dict[str, Any],
                                    requirement: Optional[Dict[str, Any]] = None, *,
                                    include_disabled_template_check: bool = False) -> Dict[str, Any]:
    """Measure every v41 semantic check without using the measurement to reject the probe."""
    checks = {
        "equality_two_opposites": dict(equality_check=True),
        "relevance_grounding": dict(relevance_check=True),
        "zero_expression_guard": dict(zero_expression_guard=True),
        "domain_property_matching": dict(domain_property_check=True),
    }
    if include_disabled_template_check:
        checks["template_requirement_matching"] = dict(template_semantic_check=True)
    baseline_ok, baseline_reason = validate_probe(
        probe, inventory, requirement, semantic_checks=False,
        equality_check=False, relevance_check=False, zero_expression_guard=False,
        domain_property_check=False, template_semantic_check=False)
    findings = {}
    for name, enabled in checks.items():
        options = {
            "equality_check": False,
            "relevance_check": False,
            "zero_expression_guard": False,
            "domain_property_check": False,
            "template_semantic_check": False,
            **enabled,
        }
        ok, reason = validate_probe(
            probe, inventory, requirement, semantic_checks=False, **options)
        findings[name] = {
            "would_reject": bool(baseline_ok and not ok),
            "reason": reason if not ok else "ok",
        }
    return {
        "mode": "log_only",
        "baseline_ok": baseline_ok,
        "baseline_reason": baseline_reason,
        "findings": findings,
        "would_reject_checks": [
            name for name, item in findings.items() if item["would_reject"]],
    }


def _target_variable_records(inventory: Dict[str, Any],
                             target_variables: Iterable[str]) -> List[Dict[str, Any]]:
    """Resolve only exact target names; never expand prefixes or inspect unrelated variables."""
    by_name = {str(v.get("name")): v for v in inventory.get("variables", [])}
    return [by_name[name] for name in target_variables if name in by_name]


def _explicit_constraint_bounds(inventory: Dict[str, Any], target_name: str) -> Dict[str, Any]:
    """Infer bounds on one variable from visible linear constraints and declared peer bounds.

    This is representation-independent: ``x <= U`` may be encoded as a variable UB or as an
    explicit row.  For multi-variable rows, interval arithmetic is used only when all peer bounds
    needed for a sound implication are finite.  No benchmark names or requirement IDs are used.
    """
    variables = {str(v.get("name")): v for v in inventory.get("variables", [])}
    lower_candidates: List[Tuple[float, str]] = []
    upper_candidates: List[Tuple[float, str]] = []

    def peer_interval(terms: Dict[str, float]) -> Tuple[Optional[float], Optional[float]]:
        minimum = maximum = 0.0
        for name, coeff in terms.items():
            var = variables.get(name, {})
            lb, ub = var.get("lb"), var.get("ub")
            if coeff >= 0:
                if lb is None:
                    minimum = None
                elif minimum is not None:
                    minimum += coeff * float(lb)
                if ub is None:
                    maximum = None
                elif maximum is not None:
                    maximum += coeff * float(ub)
            else:
                if ub is None:
                    minimum = None
                elif minimum is not None:
                    minimum += coeff * float(ub)
                if lb is None:
                    maximum = None
                elif maximum is not None:
                    maximum += coeff * float(lb)
        return minimum, maximum

    for row in inventory.get("constraints", []):
        vector = _row_vector(row)
        coefficient = float(vector.pop(target_name, 0.0))
        if abs(coefficient) <= 1e-15:
            continue
        rest_min, rest_max = peer_interval(vector)
        rhs = float(row.get("rhs", 0.0))
        sense = _normalize_sense(row.get("sense"))
        source = f"constraint:{row.get('name', '') or '<unnamed>'}"

        # a*x + rest <= rhs, with rest >= rest_min.
        if sense in ("<=", "==") and rest_min is not None:
            bound = (rhs - rest_min) / coefficient
            if coefficient > 0:
                upper_candidates.append((bound, source))
            else:
                lower_candidates.append((bound, source))
        # a*x + rest >= rhs, with rest <= rest_max.
        if sense in (">=", "==") and rest_max is not None:
            bound = (rhs - rest_max) / coefficient
            if coefficient > 0:
                lower_candidates.append((bound, source))
            else:
                upper_candidates.append((bound, source))

    return {
        "lower": max(lower_candidates, default=(None, ""), key=lambda item: item[0]),
        "upper": min(upper_candidates, default=(None, ""), key=lambda item: item[0]),
    }


def _structural_variable_property(inventory: Dict[str, Any],
                                  params: Dict[str, Any]) -> Dict[str, Any]:
    targets = list(params.get("target_variables", []))
    matched = _target_variable_records(inventory, targets)
    by_name = {str(v.get("name")): v for v in matched}
    property_name = str(params.get("property", ""))
    expected = params.get("expected_value")
    tolerance = 1e-9
    bad = []
    enforcement_sources: Dict[str, str] = {}

    if property_name == "existence":
        for name in targets:
            exists = name in by_name
            if exists is not bool(expected):
                bad.append(f"{name}:exists={exists}")
    else:
        # Validation prevents missing targets for non-existence properties. Retain this guard so
        # direct executor use cannot silently PASS an invalid target list.
        missing = [name for name in targets if name not in by_name]
        if missing:
            return {"status": "UNKNOWN", "message": "missing exact targets: " + ",".join(missing),
                    "offending": missing, "target_variables": targets,
                    "checked_property": property_name}
        for name in targets:
            var = by_name[name]
            if property_name == "vtype":
                actual = str(var.get("vtype", "")).upper()
                valid = ((expected == "binary" and actual == "B") or
                         (expected == "integer" and actual in ("I", "B")) or
                         (expected == "continuous" and actual == "C"))
                if not valid:
                    bad.append(f"{name}:vtype={actual}")
            elif property_name == "lower_bound":
                actual = var.get("lb")
                source = "variable_lower_bound"
                if actual is None or float(actual) < float(expected) - tolerance:
                    implied, implied_source = _explicit_constraint_bounds(
                        inventory, name)["lower"]
                    if implied is None or float(implied) < float(expected) - tolerance:
                        bad.append(f"{name}:effective_lb={implied},declared_lb={actual}")
                    else:
                        source = implied_source
                enforcement_sources[name] = source
            elif property_name == "upper_bound":
                actual = var.get("ub")
                source = "variable_upper_bound"
                if actual is None or float(actual) > float(expected) + tolerance:
                    implied, implied_source = _explicit_constraint_bounds(
                        inventory, name)["upper"]
                    if implied is None or float(implied) > float(expected) + tolerance:
                        bad.append(f"{name}:effective_ub={implied},declared_ub={actual}")
                    else:
                        source = implied_source
                enforcement_sources[name] = source
            else:
                return {"status": "UNKNOWN", "message": "unsupported property",
                        "offending": [], "target_variables": targets,
                        "checked_property": property_name}
    return {
        "status": "FAIL" if bad else "PASS",
        "message": ("; ".join(bad[:20]) if bad else
                    f"all {len(targets)} exact targets satisfy {property_name}={expected}"),
        "offending": bad,
        "target_variables": targets,
        "matched_variables": [v.get("name") for v in matched],
        "checked_property": property_name,
        "expected_value": expected,
        "enforcement_sources": enforcement_sources,
    }


def _stage1_fractional(inventory: Dict[str, Any], target_variables: Iterable[str],
                       tolerance: float) -> Dict[str, float]:
    out = {}
    for var in _target_variable_records(inventory, target_variables):
        value = var.get("value")
        if isinstance(value, (int, float)) and abs(value - round(value)) > tolerance:
            out[str(var.get("name"))] = round(float(value), 8)
    return out


def _execute_subprocess_probe(harness: str, probe: Dict[str, Any], candidate_code: str,
                              data: Dict[str, Any]) -> Dict[str, Any]:
    code_path = _write_tmp(candidate_code, ".py")
    probe_path = _write_tmp(json.dumps(probe), ".json")
    data_path = _write_tmp(json.dumps(_safe_problem_data(data)), ".json")
    try:
        return _run_harness(harness, [code_path, probe_path, data_path])
    finally:
        for path in (code_path, probe_path, data_path):
            try:
                os.unlink(path)
            except OSError:
                pass


def _linear_probe_from_relation(probe: Dict[str, Any]) -> Dict[str, Any]:
    params = probe.get("parameters", {}) or {}
    terms = params.get("lhs_terms", [])
    rhs = float(params.get("rhs", 0.0))
    sense = _normalize_sense(params.get("sense"))
    threshold = float(params.get("witness_threshold", 1e-6))

    def expression(name: str, multiplier: float) -> Dict[str, Any]:
        return {
            "name": name,
            "linear_expression": [
                {"var": str(term.get("var")),
                 "coeff": multiplier * float(term.get("coeff", 0.0))}
                for term in terms
            ],
            "constant": -multiplier * rhs,
            "witness_threshold": threshold,
        }

    if sense == "<=":
        expressions = [expression("above_rhs", 1.0)]
    elif sense == ">=":
        expressions = [expression("below_rhs", -1.0)]
    else:
        expressions = [expression("above_rhs", 1.0), expression("below_rhs", -1.0)]
    return {**probe, "probe_template": "maximize_linear_violation",
            "parameters": {"violation_expressions": expressions}}


def _bound_violation_probe(probe: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a semantic variable bound into full-model violation objectives."""
    params = probe.get("parameters", {}) or {}
    property_name = str(params.get("property", ""))
    expected = float(params.get("expected_value"))
    expressions = []
    for name in params.get("target_variables", []) or []:
        # Every expression is positive exactly when the semantic bound is violated.
        coefficient, constant = (
            (-1.0, expected) if property_name == "lower_bound" else
            (1.0, -expected)
        )
        expressions.append({
            "name": f"{name}_{property_name}_violation",
            "linear_expression": [{"var": str(name), "coeff": coefficient}],
            "constant": constant,
            "witness_threshold": 1e-6,
        })
    return {
        **probe,
        "probe_template": "maximize_linear_violation",
        "parameters": {"violation_expressions": expressions},
    }


def _row_vector(row: Dict[str, Any]) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for term in row.get("lhs_terms", []):
        name = str(term.get("var"))
        result[name] = result.get(name, 0.0) + float(term.get("coeff", 0.0))
    return {name: value for name, value in result.items() if abs(value) > 1e-15}


def _match_expected_row(inventory: Dict[str, Any], expected: Dict[str, Any],
                        tolerance: float = 1e-9) -> Optional[Dict[str, Any]]:
    target_name = str(expected.get("constraint_name") or "")
    target_sense = _normalize_sense(expected.get("sense"))
    target_rhs = float(expected.get("rhs", 0.0))
    target_vector = _row_vector(expected)
    for row in inventory.get("constraints", []):
        if target_name and str(row.get("name")) != target_name:
            continue
        if _normalize_sense(row.get("sense")) != target_sense:
            continue
        if abs(float(row.get("rhs", 0.0)) - target_rhs) > tolerance:
            continue
        actual = _row_vector(row)
        if set(actual) != set(target_vector):
            continue
        if any(abs(actual[name] - target_vector[name]) > tolerance for name in actual):
            continue
        return row
    return None


def _seeded_stratified_family_sample(members: List[Dict[str, Any]], sample_size: int,
                                     seed: int) -> List[Dict[str, Any]]:
    """Select one deterministic member per ordered stratum, retaining boundary coverage."""
    if sample_size <= 0 or len(members) <= sample_size:
        return list(members)
    selected_indices = {0, len(members) - 1}
    interior_slots = max(0, sample_size - len(selected_indices))
    interior_count = max(0, len(members) - 2)
    for slot in range(interior_slots):
        start = 1 + (slot * interior_count) // max(1, interior_slots)
        stop = 1 + ((slot + 1) * interior_count) // max(1, interior_slots)
        candidates = list(range(start, max(start + 1, stop)))
        digest = hashlib.sha256(
            f"{seed}|{slot}|{len(members)}".encode("utf-8")).hexdigest()
        selected_indices.add(candidates[int(digest[:16], 16) % len(candidates)])
    return [members[index] for index in sorted(selected_indices)][:sample_size]


def execute_probe(probe: Dict[str, Any], inventory: Dict[str, Any], candidate_code: str,
                  data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None,
                  seed: int = 0) -> Dict[str, Any]:
    template = probe.get("probe_template")
    params = probe.get("parameters", {}) or {}
    base = {"probe_id": probe.get("probe_id"),
            "requirement_id": probe.get("requirement_id"), "template": template}
    if template == "not_probeable":
        # Retired template. Unreachable through the selector schema; retained defensively so a
        # stale payload becomes a requirement-local non-answer instead of a silent pass.
        return {**base, "status": "UNRESOLVED",
                "message": "not_probeable is retired; requirement left unresolved",
                "solver_calls": 0}

    if template == "check_variable_property":
        structural = _structural_variable_property(inventory, params)
        property_name = str(params.get("property", ""))
        if property_name in {"lower_bound", "upper_bound"} and \
                structural["status"] != "PASS":
            derived = _bound_violation_probe(probe)
            raw = _execute_subprocess_probe(PROBE_LINEAR_HARNESS, derived, candidate_code, data)
            status = {
                "WITNESS_FOUND": "FAIL",
                "NO_WITNESS": "PASS",
            }.get(raw.get("status"), "UNKNOWN")
            return {
                **base,
                "status": status,
                "evidence_strength": (
                    "solver_witness" if status == "FAIL" else
                    "solver_no_witness" if status == "PASS" else "none"),
                "structural_status": "REQUIRES_SOLVER",
                "structural_detail": structural["message"],
                "target_variables": structural.get("target_variables", []),
                "checked_property": property_name,
                "expected_value": params.get("expected_value"),
                "declaration_observations": structural.get("offending", []),
                "witness_status": raw.get("status", "UNKNOWN"),
                "tests": raw.get("tests", []),
                "message": raw.get("message", ""),
                "post_validation_confirmed": raw.get("post_validation_confirmed", False),
                "arithmetic_replay_agrees": raw.get("arithmetic_replay_agrees", False),
                "full_model_replay": raw.get("full_model_replay"),
                "solver_calls": int(raw.get("solver_calls", 0) or 0),
            }
        result = {**base, "status": structural["status"],
                  "evidence_strength": "strong_structural",
                  "structural_status": structural["status"],
                  "structural_detail": structural["message"],
                  "target_variables": structural.get("target_variables", []),
                  "checked_property": structural.get("checked_property"),
                  "expected_value": structural.get("expected_value"),
                  "enforcement_sources": structural.get("enforcement_sources", {}),
                  "offending": structural.get("offending", []), "solver_calls": 0}
        expected = params.get("expected_value")
        if (structural["status"] != "FAIL" or params.get("property") != "vtype" or
                expected not in ("integer", "binary")):
            result["witness_status"] = "NOT_REQUIRED"
            return result
        tolerance = float(params.get("fractional_tolerance", 1e-6))
        stage1 = _stage1_fractional(inventory, params.get("target_variables", []), tolerance)
        if stage1:
            result.update({"status": "FAIL", "witness_status": "FOUND", "witness_stage": 1,
                           "fractional_values": stage1})
            return result
        witness = _execute_subprocess_probe(PROBE_FRAC_HARNESS, probe, candidate_code, data)
        result["solver_calls"] = int(witness.get("solver_calls", 0) or 0)
        if witness.get("status") == "WITNESS_FOUND":
            result.update({"status": "FAIL", "witness_status": "FOUND", "witness_stage": 2,
                           "fractional_values": witness.get("witness", {}).get("fractional_variables", {})})
        elif witness.get("status") == "NO_WITNESS":
            result.update({"status": "FAIL", "witness_status": "NOT_FOUND",
                           "witness_stage": 2,
                           "message": "structural domain failure remains; no active witness found"})
        else:
            result.update({"status": "FAIL", "witness_status": "UNKNOWN", "witness_stage": 2,
                           "message": witness.get("message", "witness search inconclusive")})
        return result

    if template == "objective_difference_probe":
        raw = _execute_subprocess_probe(
            PROBE_OBJECTIVE_DIFF_HARNESS, probe, candidate_code, data)
        outcome = raw.get("status")
        status = {
            "SENSE_MISMATCH": "FAIL",
            "DIFFERENCE_FOUND": "FAIL",
            "NO_DIFFERENCE": "PASS",
            "INCONCLUSIVE": "UNRESOLVED",
        }.get(outcome, "UNRESOLVED")
        return {**base, "status": status, "witness_status": outcome or "UNRESOLVED",
                "tests": raw.get("tests", []), "message": raw.get("message", ""),
                "candidate_sense": raw.get("candidate_sense"),
                "required_sense": raw.get("required_sense"),
                "affine_agreement": raw.get("affine_agreement"),
                "tolerance": raw.get("tolerance"),
                "evidence_strength": ("solver_witness" if status == "FAIL" else
                                      "solver_no_witness" if status == "PASS" else "none"),
                "solver_calls": int(raw.get("solver_calls", 0) or 0)}

    if template == "maximize_linear_violation":
        raw = _execute_subprocess_probe(PROBE_LINEAR_HARNESS, probe, candidate_code, data)
        status = {"WITNESS_FOUND": "FAIL", "NO_WITNESS": "PASS"}.get(raw.get("status"), "UNKNOWN")
        return {**base, "status": status, "witness_status": raw.get("status", "UNKNOWN"),
                "tests": raw.get("tests", []), "message": raw.get("message", ""),
                "post_validation_confirmed": raw.get("post_validation_confirmed", False),
                "arithmetic_replay_agrees": raw.get("arithmetic_replay_agrees", False),
                "full_model_replay": raw.get("full_model_replay"),
                "evidence_strength": ("solver_witness" if status == "FAIL" else
                                      "solver_no_witness" if status == "PASS" else "none"),
                "solver_calls": int(raw.get("solver_calls", 0) or 0)}

    if template == "linear_requirement_probe":
        derived = _linear_probe_from_relation(probe)
        raw = _execute_subprocess_probe(PROBE_LINEAR_HARNESS, derived, candidate_code, data)
        status = {"WITNESS_FOUND": "FAIL", "NO_WITNESS": "PASS"}.get(
            raw.get("status"), "UNKNOWN")
        return {**base, "status": status, "witness_status": raw.get("status", "UNKNOWN"),
                "tests": raw.get("tests", []), "message": raw.get("message", ""),
                "derived_violation_probe": derived.get("parameters", {}),
                "post_validation_confirmed": raw.get("post_validation_confirmed", False),
                "arithmetic_replay_agrees": raw.get("arithmetic_replay_agrees", False),
                "full_model_replay": raw.get("full_model_replay"),
                "evidence_strength": ("solver_witness" if status == "FAIL" else
                                      "solver_no_witness" if status == "PASS" else "none"),
                "solver_calls": int(raw.get("solver_calls", 0) or 0)}

    if template == "implication_probe":
        raw = _execute_subprocess_probe(PROBE_IMPLICATION_HARNESS, probe, candidate_code, data)
        status = {
            "WITNESS_FOUND": "FAIL", "NO_WITNESS": "PASS",
            "VACUOUS_PASS": "UNRESOLVED",
        }.get(raw.get("status"), "UNKNOWN")
        return {**base, "status": status, "witness_status": raw.get("status", "UNKNOWN"),
                "witness": raw.get("witness", {}),
                "message": raw.get("message", (
                    "antecedent infeasible; implication was not exercised"
                    if raw.get("status") == "VACUOUS_PASS" else "")),
                "tests": raw.get("tests", []),
                "violated_consequent_index": raw.get("violated_consequent_index"),
                "violation_direction": raw.get("violation_direction"),
                "recomputed_violation": raw.get("recomputed_violation"),
                "acceptance_margin": raw.get("acceptance_margin"),
                "post_validation_confirmed": raw.get("post_validation_confirmed", False),
                "arithmetic_replay_agrees": raw.get("arithmetic_replay_agrees", False),
                "full_model_replay": raw.get("full_model_replay"),
                "vacuous_antecedent": raw.get("status") == "VACUOUS_PASS",
                "evidence_strength": ("solver_witness" if status == "FAIL" else
                                      "solver_no_witness" if status == "PASS" else "none"),
                "solver_calls": int(raw.get("solver_calls", 0) or 0)}

    if template == "check_constraint_exists_by_terms":
        required = set(params.get("required_variable_names", []))
        sense = str(params.get("required_sense", "any")).lower()
        sense = {"<=": "<", ">=": ">", "==": "="}.get(sense, sense)
        for constraint in inventory.get("constraints", []):
            present = {str(t.get("var")) for t in constraint.get("lhs_terms", [])}
            sense_ok = sense in ("", "any") or str(constraint.get("sense", "")).lower() == sense
            if sense_ok and required.issubset(present):
                return {**base, "status": "PASS", "match": constraint.get("name"),
                        "message": "matching constraint found", "solver_calls": 0,
                        "evidence_strength": "weak_static"}
        return {**base, "status": "WARNING", "warning": "no compatible constraint found",
                "message": "weak static absence cannot decide the requirement",
                "solver_calls": 0, "evidence_strength": "weak_static"}

    if template == "constraint_row_probe":
        expected = params.get("expected_row", {})
        tolerance = float(params.get("tolerance", 1e-9))
        match = _match_expected_row(inventory, expected, tolerance)
        if match:
            return {**base, "status": "PASS", "match": match.get("name"),
                    "message": "exact coefficient/sense/RHS row found", "solver_calls": 0,
                    "evidence_strength": "weak_static"}
        return {**base, "status": "WARNING",
                "warning": "exact row not found; an algebraically equivalent row may exist",
                "message": "weak static mismatch requires a stronger probe",
                "solver_calls": 0, "evidence_strength": "weak_static"}

    if template == "indexed_constraint_family_probe":
        members = params.get("members")
        expected_keys = params.get("expected_index_keys")
        if isinstance(members, list) and isinstance(expected_keys, list):
            keys = [str(item.get("index_key", ""))
                    for item in members if isinstance(item, dict)]
            expected = [str(item) for item in expected_keys]
            if (not members or len(keys) != len(members) or
                    len(set(keys)) != len(keys) or keys != expected):
                return {**base, "status": "UNKNOWN",
                        "message": "indexed-family completeness validation failed",
                        "missing_index_keys": sorted(set(expected) - set(keys)),
                        "extra_index_keys": sorted(set(keys) - set(expected)),
                        "solver_calls": 0, "evidence_strength": "none"}
            sample_size = int(params.get("sample_size", INDEXED_FAMILY_SAMPLE_SIZE) or 0)
            selected = _seeded_stratified_family_sample(members, sample_size, int(seed))
            member_results = []
            total_calls = 0
            failing = None
            unknown = False
            for member in selected:
                relation = member.get("relation") or {}
                derived_probe = {
                    "probe_id": f"{probe.get('probe_id')}[{member.get('index_key')}]",
                    "requirement_id": probe.get("requirement_id"),
                    "probe_template": "linear_requirement_probe",
                    "claim": probe.get("claim", ""),
                    "parameters": {
                        **relation,
                        "witness_threshold": float(params.get("witness_threshold", 1e-6)),
                    },
                }
                raw = _execute_subprocess_probe(
                    PROBE_LINEAR_HARNESS, _linear_probe_from_relation(derived_probe),
                    candidate_code, data)
                total_calls += int(raw.get("solver_calls", 0) or 0)
                status = {"WITNESS_FOUND": "FAIL", "NO_WITNESS": "PASS"}.get(
                    raw.get("status"), "UNKNOWN")
                result = {
                    "index_key": str(member.get("index_key")),
                    "status": status,
                    "witness_status": raw.get("status", "UNKNOWN"),
                    "tests": raw.get("tests", []),
                    "post_validation_confirmed": raw.get(
                        "post_validation_confirmed", False),
                    "arithmetic_replay_agrees": raw.get(
                        "arithmetic_replay_agrees", False),
                    "full_model_replay": raw.get("full_model_replay"),
                    "solver_calls": int(raw.get("solver_calls", 0) or 0),
                }
                member_results.append(result)
                if status == "FAIL":
                    failing = result
                    break
                if status == "UNKNOWN":
                    unknown = True
            sampled = len(selected) < len(members)
            if failing is not None:
                key = failing["index_key"]
                return {**base, "status": "FAIL", "witness_status": "WITNESS_FOUND",
                        "failing_member": key,
                        "localized_requirement_id": f"{probe.get('requirement_id')}[{key}]",
                        "member_results": member_results,
                        "sampled_member_keys": [str(item.get("index_key")) for item in selected],
                        "expected_member_count": len(expected),
                        "coverage_complete": not sampled,
                        "message": f"indexed member {key} admits a violation witness",
                        "evidence_strength": "solver_witness", "solver_calls": total_calls}
            if unknown:
                return {**base, "status": "UNKNOWN", "witness_status": "UNKNOWN",
                        "member_results": member_results,
                        "sampled_member_keys": [str(item.get("index_key")) for item in selected],
                        "expected_member_count": len(expected),
                        "coverage_complete": not sampled,
                        "message": "at least one indexed member was technically unresolved",
                        "evidence_strength": "none", "solver_calls": total_calls}
            message = (
                f"no violation found on {len(selected)} seeded sampled members"
                if sampled else f"no violation found on all {len(selected)} indexed members")
            return {**base, "status": "PASS", "witness_status": "NO_WITNESS",
                    "member_results": member_results,
                    "sampled_member_keys": [str(item.get("index_key")) for item in selected],
                    "expected_member_count": len(expected),
                    "coverage_complete": not sampled, "sampled_pass": sampled,
                    "message": message, "evidence_strength": "solver_no_witness",
                    "solver_calls": total_calls}

        # Legacy v40 rows remain diagnostic-only compatible for old archives; v41 generation
        # never reaches this branch because the typed compiler requires authoritative coverage.
        expected_rows = params.get("expected_rows", [])
        tolerance = float(params.get("tolerance", 1e-9))
        matched, missing = [], []
        for index, row in enumerate(expected_rows):
            match = _match_expected_row(inventory, row, tolerance)
            if match:
                matched.append(match.get("name"))
            else:
                missing.append(row.get("constraint_name") or f"row[{index}]")
        if not missing:
            return {**base, "status": "PASS", "matched_rows": matched,
                    "message": f"all {len(matched)} indexed rows matched", "solver_calls": 0,
                    "evidence_strength": "weak_static"}
        return {**base, "status": "WARNING", "matched_rows": matched,
                "missing_rows": missing, "warning": "indexed family mismatch",
                "message": "weak static mismatch requires a stronger probe",
                "solver_calls": 0, "evidence_strength": "weak_static"}

    if template == "check_objective_terms":
        # Objective result logic (#10): a real mismatch is a FAIL, not a blanket WARNING.
        # UNKNOWN_WARNING is reserved for the cases where we genuinely could not compare --
        # extraction failure or an ambiguous comparison -- so a detected accounting error is no
        # longer downgraded to advisory noise.
        objective = inventory.get("objective", {})
        extraction_error = (not isinstance(objective, dict)
                            or objective.get("error")
                            or objective.get("terms") is None)
        if extraction_error:
            return {**base, "execution_mode": "diagnostic_only", "status": "UNKNOWN_WARNING",
                    "warning": "objective could not be extracted from the candidate",
                    "message": "objective extraction failed; comparison not possible",
                    "solver_calls": 0, "evidence_strength": "none"}

        raw_terms = objective.get("terms") or []
        terms = {}
        for term in raw_terms:
            if not isinstance(term, dict):
                continue
            coeff = evaluate_numeric(term.get("coeff"))
            if coeff is not None:
                terms[str(term.get("var"))] = coeff

        expected_coeffs = {k: evaluate_numeric(v)
                           for k, v in (params.get("required_coefficients", {}) or {}).items()}
        comparison_ambiguous = (
            any(v is None for v in expected_coeffs.values())
            or (raw_terms and not terms))
        if comparison_ambiguous:
            return {**base, "execution_mode": "diagnostic_only", "status": "UNKNOWN_WARNING",
                    "warning": "objective comparison ambiguous (non-numeric coefficients)",
                    "message": "objective comparison could not be resolved deterministically",
                    "solver_calls": 0, "evidence_strength": "none"}

        sense = str(params.get("required_sense", "")).strip().lower()
        actual_sense = str(objective.get("sense", "")).strip().lower()
        sense_mismatch = bool(sense) and sense != actual_sense

        declared_names = {
            str(item.get("name")) for item in inventory.get("variables", [])
            if isinstance(item, dict) and str(item.get("name", ""))
        }
        missing = []
        for name in params.get("required_variable_names",
                               params.get("required_var_keywords", [])):
            if name in terms or any(v.startswith(str(name)) for v in terms):
                continue
            # A declared variable absent from the extracted objective has coefficient zero.  It
            # is not undeclared/misspelled and is compared numerically below when a coefficient
            # is requested. Prefix requests still require an actual matching objective family.
            if str(name) not in declared_names:
                missing.append(str(name))

        wrong = [name for name, value in expected_coeffs.items()
                 if abs(terms.get(name, 0.0) - value) > 1e-9]

        # complete_coverage controls whether EXTRA objective terms are a failure.
        complete_coverage = bool(params.get("complete_coverage", False))
        extra = []
        if complete_coverage and expected_coeffs:
            extra = sorted(set(terms) - set(expected_coeffs))

        if sense_mismatch or missing or extra or wrong:
            detail = (f"sense_mismatch={sense_mismatch}, missing={missing}, "
                      f"extra={extra}, wrong_coefficients={wrong}")
            return {**base, "execution_mode": "diagnostic_only", "status": "UNRESOLVED", "diagnostic_verdict": "FAIL",
                    "message": f"objective mismatch ({detail})",
                    "structural_detail": detail,
                    "solver_calls": 0, "evidence_strength": "strong_structural",
                    "taxonomy": "objective_accounting_error"}
        return {**base, "execution_mode": "diagnostic_only", "status": "PASS", "message": "objective structure matches",
                "solver_calls": 0, "evidence_strength": "strong_structural"}

    return {**base, "status": "UNKNOWN", "message": "unsupported template", "solver_calls": 0}


def taxonomy_for_failure(requirement: Dict[str, Any], probe: Dict[str, Any],
                         result: Dict[str, Any]) -> str:
    """Return a deterministic category only when the probe mechanism justifies one."""
    template = probe.get("probe_template")
    category = (str(requirement.get("category", "")) + " " +
                str(requirement.get("requirement_text", ""))).lower()
    if template == "check_variable_property" or result.get("structural_status") == "FAIL":
        return "domain_or_bound_error"
    if template == "check_objective_terms":
        return "objective_accounting_error"
    if template in ("check_constraint_exists_by_terms", "constraint_row_probe",
                    "indexed_constraint_family_probe"):
        return "constraint_omission"
    if any(x in category for x in ("link", "logic", "setup", "fixed charge", "activation", "big-m")):
        return "linking_or_logic_error"
    if template == "implication_probe":
        return "linking_or_logic_error"
    if template in ("maximize_linear_violation", "linear_requirement_probe"):
        return "constraint_misspecification"
    return "mixed_or_unclear"


def repair_hint(inventory: Dict[str, Any], reason: str,
                requirement: Optional[Dict[str, Any]] = None) -> str:
    names = sorted(_inventory_names(inventory))
    constraints = [c.get("name") for c in inventory.get("constraints", [])]
    rid = (requirement or {}).get("requirement_id", "")
    return (f"Your probe was invalid: {reason}. requirement_id must remain {rid}. "
            f"For check_variable_property use only explicit exact target_variables; never use "
            f"prefixes or wildcards. available exact "
            f"variable_names={names[:50]}; constraint_names={constraints[:30]}. "
            "Return only one corrected compact JSON object.")


# =============================================================================================
# CANONICAL NORMALIZATION  (deterministic, applied before any comparison)
# =============================================================================================
VALID_SENSES = ("<=", ">=", "==")

# Pipeline-owned values. These are injected deterministically and must NEVER be generated by an
# LLM: a model-chosen tolerance silently changes what counts as a violation.
PIPELINE_OWNED_DEFAULTS = {
    "implication_probe": {"epsilon": 1e-6},
    "linear_requirement_probe": {"witness_threshold": 1e-6},
    "constraint_row_probe": {"witness_threshold": 1e-6},
    "indexed_constraint_family_probe": {"witness_threshold": 1e-6},
    "indexed_linear_family": {"witness_threshold": 1e-6},
}


def canonical_sense(sense):
    """Map aliases onto the only three valid senses; '=' becomes '=='."""
    text = str(sense or "").strip()
    mapping = {"=": "==", "==": "==", "eq": "==",
               "<": "<=", "<=": "<=", "=<": "<=", "le": "<=", "leq": "<=",
               ">": ">=", ">=": ">=", "=>": ">=", "ge": ">=", "geq": ">="}
    return mapping.get(text.lower(), text)


def evaluate_numeric(value):
    """Return an evaluated float, tolerating an arithmetic string like '30.0 - 75.0 + 0.0'.

    Numeric JSON fields are required to hold a single evaluated number; this makes a model that
    emits an expression recoverable instead of a hard failure, and guarantees comparisons operate
    on numbers.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return 0.0 if number == 0.0 else (number if math.isfinite(number) else None)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
        if not math.isfinite(number):
            return None
        return 0.0 if number == 0.0 else number
    except ValueError:
        pass
    if not re.fullmatch(r"[-+0-9eE.\s()*/]+", text):
        return None
    try:
        result = float(eval(text, {"__builtins__": {}}, {}))  # noqa: S307 - digits/operators only
        if not math.isfinite(result):
            return None
        return 0.0 if result == 0.0 else result
    except Exception:
        return None


def normalize_terms(terms):
    """Combine duplicate variables, drop zero coefficients, order canonically by variable name."""
    combined = {}
    for term in (terms or []):
        if not isinstance(term, dict):
            continue
        name = str(term.get("var", term.get("symbol", ""))).strip()
        coeff = evaluate_numeric(term.get("coeff"))
        if not name or coeff is None:
            continue
        combined[name] = combined.get(name, 0.0) + coeff
    return [{"var": name, "coeff": (0.0 if combined[name] == 0.0 else combined[name])}
            for name in sorted(combined) if abs(combined[name]) > 1e-12]


def normalize_relation(relation):
    """Canonical form: terms on the LHS, evaluated numeric RHS, one of the three valid senses.

    Also orients an inequality canonically where that is mathematically equivalent: a relation
    whose terms are all negative is flipped (negate terms and RHS, invert the sense), so
    ``-x <= -3`` and ``x >= 3`` compare equal.
    """
    if not isinstance(relation, dict):
        return None
    sense = canonical_sense(relation.get("sense"))
    if sense not in VALID_SENSES:
        return None
    terms = normalize_terms(relation.get("lhs_terms"))
    rhs = evaluate_numeric(relation.get("rhs"))
    if rhs is None:
        return None
    lhs_constant = evaluate_numeric(
        relation.get("lhs_constant", relation.get("constant", 0.0)))
    if lhs_constant is None:
        return None
    # c + a'x S b  ->  a'x S (b-c), so equivalent constant placements compare identically.
    rhs -= lhs_constant
    # Multiplying a complete relation by -1 is mathematically equivalent.  Orient by the first
    # deterministic term, not only when *all* terms happen to be negative.
    if terms and terms[0]["coeff"] < 0:
        terms = [{"var": t["var"], "coeff": -t["coeff"]} for t in terms]
        rhs = -rhs
        sense = {"<=": ">=", ">=": "<=", "==": "=="}[sense]
    rhs = 0.0 if rhs == 0.0 else rhs
    out = dict(relation)
    out["lhs_terms"] = terms
    out["rhs"] = rhs
    out["sense"] = sense
    out.pop("lhs_constant", None)
    if "constant" in out:
        out["constant"] = 0.0
    return out


def inject_pipeline_owned(probe):
    """Deterministically supply tolerances / witness thresholds / epsilon.

    Applied after normalization so an LLM-supplied value is replaced, not merely defaulted.
    """
    if not isinstance(probe, dict):
        return probe
    template = str(probe.get("probe_template", ""))
    params = probe.setdefault("parameters", {})
    for key, value in PIPELINE_OWNED_DEFAULTS.get(template, {}).items():
        params[key] = value
    return probe


def canonicalize_probe(probe):
    """Return a complete canonical copy used unchanged for judging, validation, and execution."""
    if not isinstance(probe, dict):
        return probe
    probe = deepcopy(probe)
    params = probe.get("parameters")
    if not isinstance(params, dict):
        return probe
    if isinstance(params.get("lhs_terms"), list) or params.get("rhs") is not None:
        fixed = normalize_relation(params)
        if fixed is not None:
            params.update({k: fixed[k] for k in ("lhs_terms", "rhs", "sense") if k in fixed})
    if isinstance(params.get("expected_row"), dict):
        fixed = normalize_relation(params["expected_row"])
        if fixed is not None:
            params["expected_row"] = fixed
    for key in ("expected_rows", "antecedent", "consequent"):
        if isinstance(params.get(key), list):
            rows = []
            for row in params[key]:
                fixed = normalize_relation(row) if isinstance(row, dict) else None
                rows.append(fixed if fixed is not None else row)
            params[key] = rows
    if params.get("sense") is not None:
        params["sense"] = canonical_sense(params["sense"])
    if params.get("required_sense") is not None:
        required_sense = str(params["required_sense"]).strip().lower()
        params["required_sense"] = (
            canonical_sense(required_sense)
            if required_sense not in ("minimize", "maximize", "any", "") else required_sense)
    if isinstance(params.get("required_coefficients"), dict):
        coefficients = {}
        for name in sorted(params["required_coefficients"], key=str):
            number = evaluate_numeric(params["required_coefficients"][name])
            if number is not None and abs(number) > 1e-12:
                coefficients[str(name)] = 0.0 if number == 0.0 else number
        params["required_coefficients"] = coefficients
    if params.get("expected_value") is not None and params.get("property") in (
            "lower_bound", "upper_bound"):
        value = evaluate_numeric(params["expected_value"])
        if value is not None:
            params["expected_value"] = value
    if isinstance(params.get("target_variables"), list):
        params["target_variables"] = sorted(dict.fromkeys(params["target_variables"]))
    if isinstance(params.get("required_variable_names"), list):
        params["required_variable_names"] = sorted(
            dict.fromkeys(params["required_variable_names"]))
    return inject_pipeline_owned(probe)
