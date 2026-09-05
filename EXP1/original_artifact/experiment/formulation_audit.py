"""
Layer 2 -- MAX-VIOLATION formulation audit.

Contract with the tested model's generated code:
    def build_model(data: dict) -> (model, variables)
      - model     : a gurobipy Model with all constraints added (objective may or may not be set)
      - variables : dict of decision variables under the keys given in each problem's
                    model_contract. For scalar problems (p1/p2) a value may be a single Var
                    or a dict of Vars. For retail (p3) each value is a dict keyed by
                    '|'-joined multi-index strings, e.g. variables["I"]["SKU_Basic|DC1|0|10"].

Probe principle (per requirement), all via REBUILD-then-reoptimize:
  * '>=' rule  : minimize LHS; FAIL if min < rhs        (region admits a violator)
  * '<=' rule  : maximize (LHS - rhs); FAIL if max > 0
  * '==' rule  : maximize and minimize residual (LHS-rhs); FAIL if it can leave 0 either way
  * unbounded probe -> FAIL (violation arbitrarily large)
  * variable-domain rule -> inspect var.VType / var.LB directly (definitive)
  * objective rule -> NOT probeable here (optimality is not a region property)

Every row returned has: requirement_id, source, probe_type, status
(PASS|FAIL|UNKNOWN|SKIPPED), max_violation, witness, bug_type, explanation, flagged.

Interface consumed by Exp_1.py:  run_formulation_audit(build_model, data, specs) -> list[row].
Sampling: large index families are probed on a seeded stratified SAMPLE; a sampled PASS
means "no violation found on the sampled tuples" and is reported as such.
"""
from __future__ import annotations
import random
from typing import Any, Callable, Dict, List, Optional, Tuple

TOL = 1e-6
DEFAULT_SAMPLE = 15

try:
    from gurobipy import GRB
except ImportError:
    class GRB:  # test shim / fallback constants
        MINIMIZE, MAXIMIZE = 1, -1
        CONTINUOUS, INTEGER, BINARY = "C", "I", "B"
        OPTIMAL, INFEASIBLE, INF_OR_UNBD, UNBOUNDED = 2, 3, 4, 5


# ---------------------------------------------------------------- helpers
def _data_path(data: Dict[str, Any], path: str):
    cur: Any = data
    for part in path.split("."):
        cur = cur[part]
    return cur


def _term_coef(data, term):
    """Coefficient for a linear term: literal 'coef' if present, else data lookup 'coef_path'."""
    if "coef" in term:
        return term["coef"]
    return _data_path(data, term["coef_path"])


def _spec_rhs(data, spec):
    """RHS for a linear spec: literal 'rhs' if present, else data lookup 'rhs_path'."""
    if "rhs" in spec:
        return spec["rhs"]
    return _data_path(data, spec["rhs_path"])


def _row(rid, ptype, status, explanation, bug_type=None,
         max_violation=None, witness=None, flagged=False) -> Dict[str, Any]:
    return {"requirement_id": rid, "source": "formulation_audit", "probe_type": ptype,
            "status": status, "bug_type": bug_type, "max_violation": max_violation,
            "witness": witness, "explanation": explanation, "flagged": bool(flagged)}


# ---------------------------------------------------------------- variable resolver
# Some generated models build a canonical variable correctly INSIDE the Gurobi model
# (correct VarName) but do not return it under the expected key in the variables dict.
# The generic probes therefore must not rely on the dict alone: they resolve each
# canonical name through a ladder and only give UNKNOWN if it is nowhere to be found.
def _safe_update(model) -> None:
    """model.getVarByName requires an updated model. Best-effort; no-op if unsupported."""
    try:
        model.update()
    except Exception:
        pass


def _resolve_var(model, variables, name):
    """Resolve a single canonical SCALAR variable by name. Returns Var or None.
    Ladder: (1) returned variables dict (scalar entry), (2) model.getVarByName(name),
    (3) linear scan of model.getVars() for VarName == name."""
    # 1. returned variables dictionary (ignore dict-valued entries: those are index families)
    if isinstance(variables, dict):
        v = variables.get(name)
        if v is not None and not isinstance(v, dict):
            return v
    # 2. getVarByName (needs a prior model.update())
    try:
        v = model.getVarByName(name)
        if v is not None:
            return v
    except Exception:
        pass
    # 3. scan every variable by VarName
    try:
        for v in model.getVars():
            try:
                if v.VarName == name:
                    return v
            except Exception:
                continue
    except Exception:
        pass
    return None


def _resolve_domain_items(model, variables, key):
    """Return [(display_name, Var), ...] for a domain-check key, or None if unresolvable.
    Preserves indexed-family handling (dict entry in variables) and adds the same
    name-fallback ladder for scalar variables that were not returned in the dict."""
    if isinstance(variables, dict) and isinstance(variables.get(key), dict):
        return [(f"{key}[{kk}]", vv) for kk, vv in variables[key].items()]
    var = _resolve_var(model, variables, key)
    if var is not None:
        return [(key, var)]
    return None


def _resolve_linear_expr(model, variables, data, spec):
    """Build sum(coef*var) resolving each term's variable by name.
    Returns (expr, resolved_pairs, missing_name). missing_name is the first canonical
    name that could not be resolved anywhere (or None if all resolved)."""
    expr = 0
    resolved = []
    for term in spec["lhs"]:
        name = term["var"]
        var = _resolve_var(model, variables, name)
        if var is None:
            return None, resolved, name
        resolved.append((name, var))
        expr = expr + _term_coef(data, term) * var
    return expr, resolved, None


def _scalar_witness(resolved_pairs):
    """Witness from resolved Var objects (works even when the variables dict was empty)."""
    out = {}
    for name, var in resolved_pairs:
        try:
            out[name] = round(float(var.X), 6)
        except Exception:
            pass
    return out


def _not_found_msg(name):
    return (f"variable '{name}' not found in returned variables dict, "
            f"model.getVarByName, or model.getVars(): cannot probe")


def _probe(model, sense, expr) -> Tuple[str, Optional[float]]:
    """Set objective to expr, optimize, return (status_str, objval). Disambiguates
    Gurobi/HiGHS 'infeasible-or-unbounded' via a zero-objective feasibility re-solve."""
    model.setObjective(expr, sense)
    model.optimize()
    st = model.Status
    if st == GRB.OPTIMAL:
        return "OPTIMAL", model.ObjVal
    if st == GRB.UNBOUNDED:
        return "UNBOUNDED", None
    if st == GRB.INF_OR_UNBD:
        try:
            model.setObjective(0, GRB.MINIMIZE)
            model.optimize()
            return ("UNBOUNDED", None) if model.Status == GRB.OPTIMAL else ("INFEASIBLE", None)
        except Exception:
            return "INF_OR_UNBD", None
    if st == GRB.INFEASIBLE:
        return "INFEASIBLE", None
    return f"STATUS_{st}", None


def _le_violation(model, expr) -> Tuple[Optional[bool], Optional[float]]:
    """expr = LHS - rhs. Returns (violated?, max_violation). None,None if region empty."""
    st, v = _probe(model, GRB.MAXIMIZE, expr)
    if st == "UNBOUNDED":
        return True, float("inf")
    if st in ("INFEASIBLE", "INF_OR_UNBD"):
        return None, None
    if st != "OPTIMAL":
        return None, None
    return (v > TOL), v


def _eq_violation(model, expr) -> Tuple[Optional[bool], Optional[float], str]:
    """expr = residual (LHS - rhs). Probe both directions."""
    st_hi, v_hi = _probe(model, GRB.MAXIMIZE, expr)
    if st_hi == "UNBOUNDED":
        return True, float("inf"), "residual unbounded above"
    if st_hi in ("INFEASIBLE", "INF_OR_UNBD"):
        return None, None, "region empty/unbounded (upper)"
    st_lo, v_lo = _probe(model, GRB.MINIMIZE, expr)
    if st_lo == "UNBOUNDED":
        return True, float("inf"), "residual unbounded below"
    if st_lo in ("INFEASIBLE", "INF_OR_UNBD"):
        return None, None, "region empty/unbounded (lower)"
    pos = v_hi if v_hi is not None else 0.0
    neg = v_lo if v_lo is not None else 0.0
    mag = max(pos, -neg)
    return (mag > TOL), mag, f"max_resid={pos:.4g}, min_resid={neg:.4g}"


def _extract_small_witness(variables: Dict[str, Any]) -> Dict[str, Any]:
    """Full witness for SCALAR problems (p1/p2) only. Retail witnesses are index-level."""
    out = {}
    for k, v in variables.items():
        if isinstance(v, dict):
            out[k] = {}
            for kk, vv in v.items():
                try: out[k][str(kk)] = round(float(vv.X), 6)
                except Exception: pass
        else:
            try: out[k] = round(float(v.X), 6)
            except Exception: pass
    return out


def _is_int_str(s: str) -> bool:
    return s.lstrip("-").isdigit()


def _index(subdict: Dict[str, Any]) -> Dict[Tuple, Any]:
    """Parse '|'-joined variable keys into tuples; numeric parts -> int."""
    out = {}
    for k, var in subdict.items():
        parts = str(k).split("|")
        key = tuple(int(x) if _is_int_str(x) else x for x in parts)
        out[key] = var
    return out


def _sum(terms):
    acc = 0
    for t in terms:
        acc = acc + t
    return acc


# =========================================================================
# GENERIC PROBES (scalar problems p1/p2)
# =========================================================================
def probe_linear_ge(build_model, data, spec):
    model, variables = build_model(data)
    _safe_update(model)
    expr, resolved, missing = _resolve_linear_expr(model, variables, data, spec)
    if missing is not None:
        return _row(spec["requirement_id"], "linear_ge", "UNKNOWN", _not_found_msg(missing))
    rhs = _spec_rhs(data, spec)
    st, val = _probe(model, GRB.MINIMIZE, expr)
    if st == "UNBOUNDED":
        return _row(spec["requirement_id"], "linear_ge", "FAIL",
                    f"LHS unbounded below rhs={rhs}", "constraint_not_enforced",
                    float("inf"), None, spec.get("flagged", False))
    if st in ("INFEASIBLE", "INF_OR_UNBD"):
        return _row(spec["requirement_id"], "linear_ge", "FAIL",
                    "feasible region empty", "region_empty", None, None, spec.get("flagged", False))
    if st != "OPTIMAL":
        return _row(spec["requirement_id"], "linear_ge", "UNKNOWN", f"probe status {st}")
    if val < rhs - TOL:
        return _row(spec["requirement_id"], "linear_ge", "FAIL",
                    f"region admits LHS={val} < rhs={rhs}", "constraint_not_enforced",
                    rhs - val, _scalar_witness(resolved), spec.get("flagged", False))
    return _row(spec["requirement_id"], "linear_ge", "PASS",
                f"min LHS = {val} >= rhs={rhs}: enforced", None, 0.0, None, spec.get("flagged", False))


def probe_linear_le(build_model, data, spec):
    model, variables = build_model(data)
    _safe_update(model)
    expr, resolved, missing = _resolve_linear_expr(model, variables, data, spec)
    if missing is not None:
        return _row(spec["requirement_id"], "linear_le", "UNKNOWN", _not_found_msg(missing))
    rhs = _spec_rhs(data, spec)
    violated, mv = _le_violation(model, expr - rhs)
    if violated is None:
        return _row(spec["requirement_id"], "linear_le", "UNKNOWN", "region empty/unbounded probe")
    if violated:
        return _row(spec["requirement_id"], "linear_le", "FAIL",
                    f"region admits LHS-rhs={mv} > 0 (rhs={rhs})", "constraint_not_enforced",
                    mv, _scalar_witness(resolved), spec.get("flagged", False))
    return _row(spec["requirement_id"], "linear_le", "PASS",
                f"max (LHS-rhs) = {mv} <= 0: enforced", None, mv, None, spec.get("flagged", False))


def probe_linear_eq(build_model, data, spec):
    model, variables = build_model(data)
    _safe_update(model)
    expr, resolved, missing = _resolve_linear_expr(model, variables, data, spec)
    if missing is not None:
        return _row(spec["requirement_id"], "linear_eq", "UNKNOWN", _not_found_msg(missing))
    rhs = _spec_rhs(data, spec)
    violated, mv, detail = _eq_violation(model, expr - rhs)
    if violated is None:
        return _row(spec["requirement_id"], "linear_eq", "UNKNOWN", detail)
    if violated:
        return _row(spec["requirement_id"], "linear_eq", "FAIL",
                    f"equality violable: {detail}", "constraint_not_enforced",
                    mv, _scalar_witness(resolved), spec.get("flagged", False))
    return _row(spec["requirement_id"], "linear_eq", "PASS",
                f"residual pinned to 0 ({detail})", None, mv, None, spec.get("flagged", False))


def probe_domain_integer(build_model, data, spec):
    model, variables = build_model(data)
    _safe_update(model)
    bad, unresolved = [], []
    for key in spec["vars"]:
        items = _resolve_domain_items(model, variables, key)
        if items is None:
            unresolved.append(key); continue
        for name, var in items:
            if var.VType not in (GRB.INTEGER, GRB.BINARY):
                bad.append(f"{name}={var.VType}")
    if bad:  # a found violation is definitive regardless of any unresolved names
        return _row(spec["requirement_id"], "domain_integer", "FAIL",
                    "continuous where integer required: " + "; ".join(bad[:8]),
                    "variables_not_integer", None, None, spec.get("flagged", False))
    if unresolved:
        return _row(spec["requirement_id"], "domain_integer", "UNKNOWN",
                    _not_found_msg(", ".join(unresolved)))
    return _row(spec["requirement_id"], "domain_integer", "PASS",
                "all required vars integer/binary", None, 0.0, None, spec.get("flagged", False))


def probe_domain_nonneg(build_model, data, spec):
    model, variables = build_model(data)
    _safe_update(model)
    bad, unresolved = [], []
    for key in spec["vars"]:
        items = _resolve_domain_items(model, variables, key)
        if items is None:
            unresolved.append(key); continue
        for name, var in items:
            if var.LB < -TOL:
                bad.append(f"{name} LB={var.LB}")
    if bad:  # a found negative lower bound is definitive
        return _row(spec["requirement_id"], "domain_nonneg", "FAIL",
                    "negative lower bounds: " + "; ".join(bad[:8]),
                    "negative_lower_bound", None, None, spec.get("flagged", False))
    if unresolved:
        return _row(spec["requirement_id"], "domain_nonneg", "UNKNOWN",
                    _not_found_msg(", ".join(unresolved)))
    return _row(spec["requirement_id"], "domain_nonneg", "PASS",
                "all lower bounds >= 0", None, 0.0, None, spec.get("flagged", False))


# =========================================================================
# CUSTOM PROBES -- problem 1 (Red Star Plastic)
# =========================================================================
def p1_demand(build_model, data, spec):
    cap, dem = data["cap"], data["dem"]; n = len(dem)
    worst = None
    for j in range(1, n + 1):
        model, variables = build_model(data)
        alloc = variables.get("allocation", {})
        expr = 0; any_term = False
        for key, var in alloc.items():
            i, jj = (int(x) for x in str(key).split(","))
            if jj == j and cap[i-1] >= cap[j-1]:
                expr = expr + 1.0 * var; any_term = True
        if not any_term:
            return _row("R1", "custom", "FAIL", f"no allocation serves demand class {j}",
                        "constraint_not_enforced")
        st, val = _probe(model, GRB.MINIMIZE, expr)
        if st == "OPTIMAL" and val < dem[j-1] - TOL:
            worst = worst or _row("R1", "custom", "FAIL",
                                  f"class {j}: region admits served={val} < dem={dem[j-1]}",
                                  "constraint_not_enforced", dem[j-1]-val,
                                  _extract_small_witness(variables))
        elif st == "UNBOUNDED":
            worst = worst or _row("R1", "custom", "FAIL", f"class {j}: served unbounded below",
                                  "constraint_not_enforced", float("inf"))
        elif st != "OPTIMAL":
            return _row("R1", "custom", "UNKNOWN", f"class {j}: probe status {st}")
    return worst or _row("R1", "custom", "PASS", "every demand class enforced", None, 0.0)


def p1_substitution_direction(build_model, data, spec):
    cap = data["cap"]
    model, variables = build_model(data)
    alloc = variables.get("allocation", {})
    expr = 0; any_illegal = False
    for key, var in alloc.items():
        i, j = (int(x) for x in str(key).split(","))
        if cap[i-1] < cap[j-1]:
            expr = expr + 1.0 * var; any_illegal = True
    if not any_illegal:
        return _row("R2", "custom", "PASS", "no illegal-direction allocation vars exist", None, 0.0)
    st, val = _probe(model, GRB.MAXIMIZE, expr)
    if st == "UNBOUNDED" or (st == "OPTIMAL" and val > TOL):
        return _row("R2", "custom", "FAIL",
                    f"illegal substitution reachable ({val if st=='OPTIMAL' else 'unbounded'})",
                    "constraint_not_enforced", val if st == "OPTIMAL" else float("inf"),
                    _extract_small_witness(variables) if st == "OPTIMAL" else None)
    if st != "OPTIMAL":
        return _row("R2", "custom", "UNKNOWN", f"probe status {st}")
    return _row("R2", "custom", "PASS", "illegal substitutions forced to 0", None, 0.0)


def p1_conservation(build_model, data, spec):
    n = len(data["dem"])
    for i in range(1, n + 1):
        model, variables = build_model(data)
        produced = variables.get("produced", {}); alloc = variables.get("allocation", {})
        p_i = produced.get(str(i), produced.get(i))
        if p_i is None:
            return _row("R3", "custom", "UNKNOWN", f"produced[{i}] not exposed")
        expr = -1.0 * p_i; any_term = False
        for key, var in alloc.items():
            ii, j = (int(x) for x in str(key).split(","))
            if ii == i:
                expr = expr + 1.0 * var; any_term = True
        if not any_term:
            continue
        st, val = _probe(model, GRB.MAXIMIZE, expr)
        if st == "UNBOUNDED" or (st == "OPTIMAL" and val > TOL):
            return _row("R3", "custom", "FAIL",
                        f"type {i}: usage can exceed production by {val if st=='OPTIMAL' else 'unbounded'}",
                        "constraint_not_enforced", val if st == "OPTIMAL" else float("inf"),
                        _extract_small_witness(variables) if st == "OPTIMAL" else None)
        if st != "OPTIMAL":
            return _row("R3", "custom", "UNKNOWN", f"type {i}: probe status {st}")
    return _row("R3", "custom", "PASS", "usage <= production for all types", None, 0.0)


# =========================================================================
# CUSTOM PROBES -- problem 3 (retail F8). Multi-index, '|'-joined keys.
# All build the model ONCE, then reoptimize per sampled probe.
# =========================================================================
def _retail_dims(data):
    P = data["products"]; L = data["locations"]; T = data["periods"]
    SL = data["shelf_life"]
    dem = {(p, l, t): data["demand_curve"][p][t] * data["demand_share"][l]
           for p in P for l in L for t in range(T)}
    return P, L, T, SL, dem


def _sample(rng, items, spec):
    k = spec.get("sample", DEFAULT_SAMPLE)
    if len(items) <= k:
        return items, len(items)
    return rng.sample(items, k), len(items)


def retail_equality(build_model, data, spec):
    """R1 fresh inflow, R2 aging, R3 waste -- definitional equalities. Two-direction probe."""
    rid = spec["requirement_id"]
    P, L, T, SL, dem = _retail_dims(data)
    model, variables = build_model(data)
    I = _index(variables.get("I", {})); S = _index(variables.get("sales", {}))
    Q = _index(variables.get("Q", {})); W = _index(variables.get("W", {}))
    residuals: List[Tuple[str, Any]] = []
    missing = 0

    if rid == "R1":                       # I[p,l,t,SL] - Q[p,l,t] == 0
        for p in P:
            for l in L:
                for t in range(T):
                    iv = I.get((p, l, t, SL[p])); qv = Q.get((p, l, t))
                    if iv is None or qv is None: missing += 1; continue
                    residuals.append((f"{p}|{l}|{t}", iv - qv))
    elif rid == "R2":                     # I[t+1,r] - I[t,r+1] + sales[t,r+1] == 0
        for p in P:
            for l in L:
                for t in range(T - 1):
                    for r in range(1, SL[p]):
                        a = I.get((p, l, t+1, r)); b = I.get((p, l, t, r+1)); s = S.get((p, l, t, r+1))
                        if a is None or b is None or s is None: missing += 1; continue
                        residuals.append((f"{p}|{l}|{t}->{t+1}|r{r}", a - b + s))
    elif rid == "R3":                     # W - I[t,1] + sales[t,1] == 0
        for p in P:
            for l in L:
                for t in range(T):
                    w = W.get((p, l, t)); i1 = I.get((p, l, t, 1)); s1 = S.get((p, l, t, 1))
                    if w is None or i1 is None or s1 is None: missing += 1; continue
                    residuals.append((f"{p}|{l}|{t}", w - i1 + s1))
    else:
        return _row(rid, "retail_equality", "UNKNOWN", f"no equality definition for {rid}")

    if not residuals:
        return _row(rid, "retail_equality", "UNKNOWN",
                    f"could not build any residual (missing vars: {missing}); check key convention")

    rng = random.Random(spec.get("seed", 0))
    sample, total = _sample(rng, residuals, spec)
    worst_mag = 0.0
    for label, expr in sample:
        violated, mag, detail = _eq_violation(model, expr)
        if violated is None:
            return _row(rid, "retail_equality", "UNKNOWN", f"{label}: {detail}")
        if violated:
            return _row(rid, "retail_equality", "FAIL",
                        f"equality violable at {label}: {detail}", "constraint_not_enforced",
                        mag, {"index": label, "violation": mag}, spec.get("flagged", False))
        worst_mag = max(worst_mag, mag)
    return _row(rid, "retail_equality", "PASS",
                f"pinned on {len(sample)}/{total} sampled tuples (max residual {worst_mag:.3g})",
                None, worst_mag, None, spec.get("flagged", False))


def retail_sales_availability(build_model, data, spec):
    """R4: sales[p,l,t,r] <= I[p,l,t,r]. Maximize (sales - I)."""
    P, L, T, SL, _ = _retail_dims(data)
    model, variables = build_model(data)
    I = _index(variables.get("I", {})); S = _index(variables.get("sales", {}))
    keys = [k for k in S.keys() if k in I]
    if not keys:
        return _row("R4", "retail_sales_availability", "UNKNOWN", "no matching sales/I vars")
    rng = random.Random(spec.get("seed", 0))
    sample, total = _sample(rng, keys, spec)
    worst = 0.0
    for k in sample:
        violated, mv = _le_violation(model, S[k] - I[k])
        if violated is None:
            return _row("R4", "retail_sales_availability", "UNKNOWN", f"probe empty at {k}")
        if violated:
            return _row("R4", "retail_sales_availability", "FAIL",
                        f"sales can exceed inventory at {k} by {mv}", "constraint_not_enforced",
                        mv, {"index": "|".join(map(str, k)), "violation": mv})
        worst = max(worst, mv)
    return _row("R4", "retail_sales_availability", "PASS",
                f"sales<=inventory on {len(sample)}/{total} sampled layers", None, worst)


def retail_production_cap(build_model, data, spec):
    """R5: sum_l Q[p,l,t] <= production_cap[p][t]. Maximize (sum - cap)."""
    P, L, T, SL, _ = _retail_dims(data)
    model, variables = build_model(data)
    Q = _index(variables.get("Q", {}))
    pairs = [(p, t) for p in P for t in range(T)]
    rng = random.Random(spec.get("seed", 0))
    sample, total = _sample(rng, pairs, spec)
    worst = 0.0
    for (p, t) in sample:
        terms = [Q[(p, l, t)] for l in L if (p, l, t) in Q]
        if not terms:
            continue
        cap = data["production_cap"][p][t]
        violated, mv = _le_violation(model, _sum(terms) - cap)
        if violated is None:
            return _row("R5", "retail_production_cap", "UNKNOWN", f"probe empty at {p},{t}")
        if violated:
            return _row("R5", "retail_production_cap", "FAIL",
                        f"production can exceed cap at ({p},t{t}) by {mv} (cap={cap})",
                        "constraint_not_enforced", mv, {"index": f"{p}|t{t}", "violation": mv})
        worst = max(worst, mv)
    return _row("R5", "retail_production_cap", "PASS",
                f"production<=cap on {len(sample)}/{total} sampled (p,t)", None, worst)


def retail_cold_cap(build_model, data, spec):
    """R6: sum_p cold_usage[p]*sum_r I[p,l,t,r] <= cold_capacity[l]. Maximize (usage - cap)."""
    P, L, T, SL, _ = _retail_dims(data)
    model, variables = build_model(data)
    I = _index(variables.get("I", {}))
    use = data["cold_usage"]; capL = data["cold_capacity"]
    pairs = [(l, t) for l in L for t in range(T)]
    rng = random.Random(spec.get("seed", 0))
    sample, total = _sample(rng, pairs, spec)
    worst = 0.0
    for (l, t) in sample:
        terms = []
        for p in P:
            for r in range(1, SL[p] + 1):
                if (p, l, t, r) in I:
                    terms.append(use[p] * I[(p, l, t, r)])
        if not terms:
            continue
        violated, mv = _le_violation(model, _sum(terms) - capL[l])
        if violated is None:
            return _row("R6", "retail_cold_cap", "UNKNOWN", f"probe empty at {l},{t}")
        if violated:
            return _row("R6", "retail_cold_cap", "FAIL",
                        f"cold usage can exceed capacity at ({l},t{t}) by {mv} (cap={capL[l]:.1f})",
                        "constraint_not_enforced", mv, {"index": f"{l}|t{t}", "violation": mv})
        worst = max(worst, mv)
    return _row("R6", "retail_cold_cap", "PASS",
                f"cold usage<=capacity on {len(sample)}/{total} sampled (l,t)", None, worst)


def retail_waste_cap(build_model, data, spec):
    """R7: sum(W) <= 0.02 * total_demand. Maximize total waste."""
    P, L, T, SL, dem = _retail_dims(data)
    total_dem = sum(dem.values())
    cap = data["constraints"]["waste_limit_pct"] * total_dem
    model, variables = build_model(data)
    W = _index(variables.get("W", {}))
    if not W:
        return _row("R7", "retail_waste_cap", "UNKNOWN", "no W vars exposed")
    expr = _sum(list(W.values()))
    violated, mv = _le_violation(model, expr - cap)
    if violated is None:
        return _row("R7", "retail_waste_cap", "UNKNOWN", "waste probe empty/unbounded region")
    if violated:
        return _row("R7", "retail_waste_cap", "FAIL",
                    f"total waste can reach cap+{mv} (cap={cap:.2f})", "constraint_not_enforced",
                    mv, {"waste_cap": cap, "excess": mv})
    return _row("R7", "retail_waste_cap", "PASS",
                f"max total waste <= cap={cap:.2f} (slack {mv:.3g})", None, mv)


def retail_demand_and_subst(build_model, data, spec):
    """R8: (a) demand balance equality sum_q V[q,p,l,t]+lost == demand;
            (b) illegal-direction substitution forced to 0 (only Premium->Basic + self allowed)."""
    P, L, T, SL, dem = _retail_dims(data)
    model, variables = build_model(data)
    V = _index(variables.get("V", {})); lost = _index(variables.get("lost", {}))
    if not V:
        return _row("R8", "retail_demand_and_subst", "UNKNOWN",
                    "V (substitution) vars not exposed; cannot audit substitution behaviorally")
    allowed = {(p, p) for p in P}
    for edge in data["network"]["sub_edges"]:
        a, b = edge[0], edge[1]
        allowed.add((b, a))                       # pinned: b (Premium) may serve a (Basic)

    # (b) illegal substitution: maximize sum of V[q,p,...] with (q,p) not allowed
    illegal_terms = [var for (q, p, l, t), var in V.items() if (q, p) not in allowed]
    if illegal_terms:
        violated, mv = _le_violation(model, _sum(illegal_terms))
        if violated:
            return _row("R8", "retail_demand_and_subst", "FAIL",
                        f"illegal-direction substitution reachable (sum can reach {mv})",
                        "constraint_not_enforced", mv, {"illegal_substitution": mv})

    # (a) demand balance equality, sampled over (p,l,t)
    triples = [(p, l, t) for p in P for l in L for t in range(T)]
    rng = random.Random(spec.get("seed", 0))
    sample, total = _sample(rng, triples, spec)
    worst = 0.0
    for (p, l, t) in sample:
        serve = [var for (q, pp, ll, tt), var in V.items() if pp == p and ll == l and tt == t]
        lv = lost.get((p, l, t))
        if not serve or lv is None:
            continue
        resid = _sum(serve) + lv - dem[(p, l, t)]
        violated, mag, detail = _eq_violation(model, resid)
        if violated is None:
            return _row("R8", "retail_demand_and_subst", "UNKNOWN", f"balance probe empty at {p},{l},{t}")
        if violated:
            return _row("R8", "retail_demand_and_subst", "FAIL",
                        f"demand balance violable at ({p},{l},t{t}): {detail}", "constraint_not_enforced",
                        mag, {"index": f"{p}|{l}|t{t}", "violation": mag})
        worst = max(worst, mag)
    return _row("R8", "retail_demand_and_subst", "PASS",
                f"substitution direction + demand balance enforced ({len(sample)}/{total} sampled)",
                None, worst)


# =========================================================================
# REGISTRIES + DISPATCH
# =========================================================================
def probe_objective_value(build_model, data, spec):
    """Layer-2 objective witness. Re-optimize the model's OWN objective and compare the
    achievable optimum to the gold objective (data['_gold_objective']).

    Witness semantics (mirror the region probes):
      * achievable optimum BETTER than gold -> feasible region too LOOSE (constraint
        missing/weak): model reaches a solution the true problem forbids. FAIL,
        bug_type='objective_region_too_loose'.
      * achievable optimum WORSE than gold (cannot reach gold) -> region too TIGHT
        (over-restrictive/extraneous constraint): true optimum excluded. FAIL,
        bug_type='objective_region_too_tight'.
      * matches gold within frozen tolerance -> PASS.
    'Better' respects sense (min: smaller; max: larger). Gold absent -> UNKNOWN.
    """
    rid = spec.get("requirement_id")
    flagged = spec.get("flagged", False)
    gold = data.get("_gold_objective")
    if gold is None:
        return _row(rid, "objective_value", "UNKNOWN",
                    "no _gold_objective on this instance; Layer-2 optimality not checked",
                    None, None, None, flagged)
    try:
        gold = float(gold)
    except (TypeError, ValueError):
        return _row(rid, "objective_value", "UNKNOWN", "gold not numeric", None, None, None, flagged)

    model, variables = build_model(data)
    _safe_update(model)
    try:
        sense = model.ModelSense      # 1 = MINIMIZE, -1 = MAXIMIZE
    except Exception:
        sense = 1
    model.optimize()
    st = model.Status
    if st == GRB.INFEASIBLE:
        return _row(rid, "objective_value", "FAIL",
                    "model infeasible: feasible region empty (over-restrictive)",
                    "objective_region_too_tight", float("inf"), None, flagged)
    if st in (GRB.UNBOUNDED, GRB.INF_OR_UNBD):
        return _row(rid, "objective_value", "FAIL",
                    "model unbounded: objective improves without limit (region too loose)",
                    "objective_region_too_loose", float("inf"), None, flagged)
    if st != GRB.OPTIMAL:
        return _row(rid, "objective_value", "UNKNOWN", f"solve status {st}",
                    None, None, None, flagged)

    opt = model.ObjVal
    gap = opt - gold
    tol = max(0.01, 1e-6 * abs(gold))     # frozen objective tolerance (matches checkers)
    if abs(gap) <= tol:
        return _row(rid, "objective_value", "PASS",
                    f"model optimum {opt} matches gold {gold} within tol",
                    None, abs(gap), None, flagged)
    better = (opt < gold - tol) if sense == 1 else (opt > gold + tol)
    if better:
        return _row(rid, "objective_value", "FAIL",
                    f"model reaches {opt}, BETTER than gold {gold}: region too loose "
                    f"(constraint missing/weak)",
                    "objective_region_too_loose", abs(gap), None, flagged)
    return _row(rid, "objective_value", "FAIL",
                f"model best {opt}, cannot reach gold {gold}: region too tight "
                f"(over-restrictive/extraneous constraint)",
                "objective_region_too_tight", abs(gap), None, flagged)


GENERIC = {
    "linear_ge": probe_linear_ge,
    "linear_le": probe_linear_le,
    "linear_eq": probe_linear_eq,
    "domain_integer": probe_domain_integer,
    "domain_nonneg": probe_domain_nonneg,
    "objective_value": probe_objective_value,
}
PROBE_BUILDERS = {
    "p1_demand": p1_demand,
    "p1_substitution_direction": p1_substitution_direction,
    "p1_conservation": p1_conservation,
    "retail_equality": retail_equality,
    "retail_sales_availability": retail_sales_availability,
    "retail_production_cap": retail_production_cap,
    "retail_cold_cap": retail_cold_cap,
    "retail_waste_cap": retail_waste_cap,
    "retail_demand_and_subst": retail_demand_and_subst,
}


def run_formulation_audit(build_model: Callable, data: Dict[str, Any],
                          specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for spec in specs:
        rid = spec.get("requirement_id"); stype = spec.get("type")
        flagged = spec.get("flagged", False)
        if stype in ("not_probeable", "layer1_only"):
            rows.append(_row(rid, stype, "SKIPPED",
                             spec.get("note", "handled by Layer 1 / gold comparison"),
                             None, None, None, flagged))
            continue
        try:
            if stype == "custom":
                probe = PROBE_BUILDERS.get(spec.get("probe"))
                if probe is None:
                    rows.append(_row(rid, "custom", "UNKNOWN",
                                     f"no probe implemented named '{spec.get('probe')}'"))
                    continue
                r = probe(build_model, data, spec)
            elif stype in GENERIC:
                r = GENERIC[stype](build_model, data, spec)
            else:
                rows.append(_row(rid, str(stype), "UNKNOWN", f"unknown probe type '{stype}'"))
                continue
            # ensure flagged flag propagates from spec even if probe didn't set it
            if flagged and not r.get("flagged"):
                r["flagged"] = True
            rows.append(r)
        except Exception as e:
            rows.append(_row(rid, str(stype), "UNKNOWN", f"{type(e).__name__}: {e}", "probe_error"))
    return rows