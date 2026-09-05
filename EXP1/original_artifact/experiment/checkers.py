"""
Layer 1 (output-level) frozen checkers -- now fully DATA-DRIVEN so they can run on
any perturbed instance (required for the Layer-2 multi-instance audit).

Each checker: check(data, solution) -> ("PASS"|"FAIL", detail). Reads ONLY data + solution.
"""
TOL = 1e-6

# Objective-match tolerance (pre-registered Stage-0 decision).
# Golds are stored ROUNDED (<=2 decimals), so an exactly-correct model can differ from the
# stored gold by up to ~0.005. A hard 1e-4 absolute tolerance wrongly flags such correct
# answers as loud bugs. We therefore use a combined relative+absolute tolerance that (a)
# absorbs gold rounding and large-magnitude golds, and (b) is still far tighter than any
# genuine objective error in these problems. Do NOT loosen without re-verification.
OBJ_ABS_TOL = 0.01     # absorbs 2-decimal rounding (worst case 0.005) with margin
OBJ_REL_TOL = 1e-6     # scales for large golds (e.g. 316282*1e-6 = 0.32)

def objective_close(a, b):
    """True if objective values a,b match within the pre-registered combined tolerance."""
    try:
        a = float(a); b = float(b)
    except (TypeError, ValueError):
        return False
    return abs(a - b) <= max(OBJ_ABS_TOL, OBJ_REL_TOL * abs(b))
def _is_int(x): return abs(x - round(x)) <= TOL

# ===================== PROBLEM 2 (trucks) -- data-driven =====================
# data = {"cost":{"A":..,"B":..},
#         "coef":{"matA":{"A":..,"B":..}, "matB":{...}, "matC":{...}},
#         "rhs":{"matA":..,"matB":..,"matC":..}}
def _p2_material(m):
    def f(data, sol):
        A = sol["solution"]["trucks_A"]; B = sol["solution"]["trucks_B"]
        c = data["coef"][m]; delivered = c["A"]*A + c["B"]*B; need = data["rhs"][m]
        return ("PASS" if delivered >= need - TOL else "FAIL",
                f"{m}: delivered={delivered} (need>={need})")
    f.__name__ = f"p2_{m}_min"
    return f

def p2_R4_nonneg(data, sol):
    A = sol["solution"]["trucks_A"]; B = sol["solution"]["trucks_B"]
    return ("PASS" if A >= -TOL and B >= -TOL else "FAIL", f"trucks_A={A}, trucks_B={B}")

def p2_R5_integer(data, sol):   # AMBIGUITY-FLAGGED
    A = sol["solution"]["trucks_A"]; B = sol["solution"]["trucks_B"]
    return ("PASS" if _is_int(A) and _is_int(B) else "FAIL", f"trucks_A={A}, trucks_B={B}")

def p2_R6_coef(data, sol):
    A = sol["solution"]["trucks_A"]; B = sol["solution"]["trucks_B"]
    recomputed = data["cost"]["A"]*A + data["cost"]["B"]*B
    reported = sol.get("objective")
    ok = reported is not None and objective_close(recomputed, reported)
    return ("PASS" if ok else "FAIL", f"recomputed={recomputed}, reported={reported}")

def p2_R6_opt(data, sol):
    # optimality vs gold: only valid on the CANONICAL instance (data carries its gold).
    A = sol["solution"]["trucks_A"]; B = sol["solution"]["trucks_B"]
    recomputed = data["cost"]["A"]*A + data["cost"]["B"]*B
    gold = data.get("_gold_objective")
    if gold is None:
        return ("PASS", "no gold on this instance; optimality not checked")
    return ("PASS" if objective_close(recomputed, gold) else "FAIL", f"recomputed={recomputed}, gold={gold}")

# ===================== PROBLEM 1 (Red Star Plastic) -- already data-driven =====================
def _p1_unpack(data, sol):
    cap=data["cap"]; dem=data["dem"]; vcost=data["vcost"]; FIX=data["fixed"]
    s=sol["solution"]; produced={int(k):v for k,v in s["produced"].items()}
    allocation={}
    for k,v in s.get("allocation",{}).items():
        i,j=k.split(","); allocation[(int(i),int(j))]=v
    return cap,dem,vcost,FIX,produced,allocation

def p1_R1_demand(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol); n=len(dem); bad=[]
    for j in range(1,n+1):
        served=sum(u for (i,jj),u in allocation.items() if jj==j and cap[i-1]>=cap[j-1])
        if served<dem[j-1]-TOL: bad.append(f"class {j}: served={served}<dem={dem[j-1]}")
    return ("PASS" if not bad else "FAIL","; ".join(bad) or "all demands met")

def p1_R2_subst_direction(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol)
    bad=[f"({i}->{j})" for (i,j),u in allocation.items() if u>TOL and cap[i-1]<cap[j-1]]
    return ("PASS" if not bad else "FAIL",("illegal subst: "+", ".join(bad)) if bad else "ok")

def p1_R3_conservation(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol); n=len(dem); bad=[]
    for i in range(1,n+1):
        used=sum(u for (ii,j),u in allocation.items() if ii==i)
        if used>produced.get(i,0)+TOL: bad.append(f"type {i}: used={used}>prod={produced.get(i,0)}")
    return ("PASS" if not bad else "FAIL","; ".join(bad) or "ok")

def p1_R4_fixed_cost_linking(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol); n=len(dem)
    var=sum(vcost[i-1]*produced.get(i,0) for i in range(1,n+1))
    implied=FIX*sum(1 for i in range(1,n+1) if produced.get(i,0)>TOL)
    rep=sol.get("objective")
    ok=rep is not None and abs((rep-var)-implied)<=1e-4
    return ("PASS" if ok else "FAIL", f"reported-var={None if rep is None else rep-var}, implied_fixed={implied}")

def p1_R5_integer(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol)
    bad=[f"prod[{i}]={v}" for i,v in produced.items() if not _is_int(v)]
    bad+=[f"alloc[{i},{j}]={v}" for (i,j),v in allocation.items() if not _is_int(v)]
    return ("PASS" if not bad else "FAIL","; ".join(bad) or "all integer")

def p1_R6_nonneg(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol)
    bad=[f"prod[{i}]={v}" for i,v in produced.items() if v<-TOL]
    bad+=[f"alloc[{i},{j}]={v}" for (i,j),v in allocation.items() if v<-TOL]
    return ("PASS" if not bad else "FAIL","; ".join(bad) or "all nonneg")

def p1_R7_coef(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol); n=len(dem)
    var=sum(vcost[i-1]*produced.get(i,0) for i in range(1,n+1))
    fixed=FIX*sum(1 for i in range(1,n+1) if produced.get(i,0)>TOL)
    rec=var+fixed; rep=sol.get("objective")
    ok=rep is not None and abs(rec-rep)<=1e-4
    return ("PASS" if ok else "FAIL", f"recomputed={rec}, reported={rep}")

def p1_R7_opt(data,sol):
    cap,dem,vcost,FIX,produced,allocation=_p1_unpack(data,sol); n=len(dem)
    var=sum(vcost[i-1]*produced.get(i,0) for i in range(1,n+1))
    fixed=FIX*sum(1 for i in range(1,n+1) if produced.get(i,0)>TOL)
    rec=var+fixed; gold=data.get("_gold_objective")
    if gold is None: return ("PASS","no gold on this instance")
    return ("PASS" if objective_close(rec, gold) else "FAIL", f"recomputed={rec}, gold={gold}")

REGISTRY = {
    "p1": {"R1":[("p1.R1.C1",p1_R1_demand)],
           "R2":[("p1.R2.C1",p1_R2_subst_direction)],
           "R3":[("p1.R3.C1",p1_R3_conservation)],
           "R4":[("p1.R4.C1",p1_R4_fixed_cost_linking)],
           "R5":[("p1.R5.C1",p1_R5_integer)],
           "R6":[("p1.R6.C1",p1_R6_nonneg)],
           "R7":[("p1.R7.C1",p1_R7_coef),("p1.R7.C2",p1_R7_opt)]},
}

# Which requirements are FEASIBILITY (region) requirements -> used by the multi-instance audit.
# Objective coef/opt are excluded (they are not feasible-region constraints).
FEASIBILITY_REQUIREMENTS = {
    "p1": ["R1","R2","R3","R5","R6"],   # R4 fixed-cost + R7 objective are cost-accounting, not region
}


# ============================================================================
# SCALED PROBLEMS (p3-p10) -- Layer 1 checkers built from the SAME linear specs
# used by the Layer 2 generic probes, plus small custom checkers for logical /
# semi-continuous / objective requirements. Solutions use flat scalar keys.
# ============================================================================
def _lin_checker(lhs, sense, rhs):
    def f(data, sol):
        s = sol["solution"]
        try:
            val = sum(c * s[v] for v, c in lhs)
        except KeyError as e:
            return ("FAIL", f"missing solution key {e}")
        if sense == ">=":  ok = val >= rhs - TOL
        elif sense == "<=": ok = val <= rhs + TOL
        else:              ok = abs(val - rhs) <= TOL
        return ("PASS" if ok else "FAIL", f"value={val} {sense} {rhs}")
    return f

def _domain_checker(keys, kind):
    def f(data, sol):
        s = sol["solution"]; bad = []
        for k in keys:
            if k not in s: bad.append(f"{k}:missing"); continue
            v = s[k]
            if kind == "int" and not _is_int(v): bad.append(f"{k}={v}")
            if kind == "nonneg" and v < -TOL: bad.append(f"{k}={v}")
        return ("PASS" if not bad else "FAIL", "; ".join(bad) or "ok")
    return f

def _obj_coef_checker(terms):
    def f(data, sol):
        s = sol["solution"]
        try:
            rec = sum(c * s[v] for v, c in terms)
        except KeyError as e:
            return ("FAIL", f"missing solution key {e}")
        rep = sol.get("objective")
        ok = rep is not None and objective_close(rec, rep)
        return ("PASS" if ok else "FAIL", f"recomputed={rec}, reported={rep}")
    return f

def _obj_opt_checker(terms):
    def f(data, sol):
        s = sol["solution"]; gold = data.get("_gold_objective")
        if gold is None:
            return ("PASS", "no gold on this instance; optimality not checked")
        try:
            rec = sum(c * s[v] for v, c in terms)
        except KeyError as e:
            return ("FAIL", f"missing solution key {e}")
        return ("PASS" if objective_close(rec, gold) else "FAIL", f"recomputed={rec}, gold={gold}")
    return f

def _implication_zero_checker(if_pos, then_zero):
    def f(data, sol):
        s = sol["solution"]
        if s.get(if_pos, 0) > TOL and abs(s.get(then_zero, 0)) > TOL:
            return ("FAIL", f"{if_pos}>0 but {then_zero}={s.get(then_zero)}")
        return ("PASS", f"{if_pos}>0 => {then_zero}=0 holds")
    return f

def _implication_pos_checker(if_pos, then_pos):
    def f(data, sol):
        s = sol["solution"]
        if s.get(if_pos, 0) > TOL and s.get(then_pos, 0) <= TOL:
            return ("FAIL", f"{if_pos}>0 but {then_pos}={s.get(then_pos)}")
        return ("PASS", f"{if_pos}>0 => {then_pos}>0 holds")
    return f

def _semicontinuous_checker(vars_, min_batch):
    def f(data, sol):
        s = sol["solution"]; bad = []
        for v in vars_:
            x = s.get(v, 0)
            if x > TOL and x < min_batch - TOL:
                bad.append(f"{v}={x} in (0,{min_batch})")
        return ("PASS" if not bad else "FAIL", "; ".join(bad) or "each var 0 or >=min_batch")
    return f

def _build_scaled_registry():
    import json as _json, os as _os
    specs_path = _os.path.join(_os.path.dirname(__file__), "checker_specs.json")
    if not _os.path.exists(specs_path):
        return {}
    all_specs = _json.load(open(specs_path))
    reg = {}
    _SENSE = {"linear_ge": ">=", "linear_le": "<=", "linear_eq": "=="}
    for pid, cs in all_specs.items():
        if cs is None: continue
        pkey = f"p{pid}"; entries = {}
        # linear constraint checkers (from shared specs)
        for spec in cs.get("linear", []):
            st = spec["type"]
            if st not in _SENSE:  # domain specs may appear in 'linear' list for some problems; skip
                continue
            rid = spec["requirement_id"]
            lhs = [(t["var"], t["coef"]) for t in spec["lhs"]]
            fn = _lin_checker(lhs, _SENSE[st], spec["rhs"])
            fn.__name__ = f"{pkey}_{rid}_lin"
            entries.setdefault(rid, []).append((f"{pkey}.{rid}.C1", fn))
        # domain checkers referenced from the full linear spec list too
        for spec in cs.get("linear", []):
            if spec["type"] == "domain_integer":
                rid = spec["requirement_id"]; fn = _domain_checker(spec["vars"], "int")
                fn.__name__ = f"{pkey}_{rid}_int"; entries.setdefault(rid, []).append((f"{pkey}.{rid}.C1", fn))
            if spec["type"] == "domain_nonneg":
                rid = spec["requirement_id"]; fn = _domain_checker(spec["vars"], "nonneg")
                fn.__name__ = f"{pkey}_{rid}_nn"; entries.setdefault(rid, []).append((f"{pkey}.{rid}.C1", fn))
        # explicit domain lists (problems that separated them)
        for rid_key, kind in [("domain_int", "int"), ("domain_nonneg", "nonneg")]:
            if cs.get(rid_key):
                # find the requirement id by matching: use a synthetic id
                pass
        # logical implications
        for imp in cs.get("logical_implications", []):
            rid = imp["rid"]
            if "then_zero" in imp:
                fn = _implication_zero_checker(imp["if_pos"], imp["then_zero"])
            else:
                fn = _implication_pos_checker(imp["if_pos"], imp["then_pos"])
            fn.__name__ = f"{pkey}_{rid}_impl"
            entries.setdefault(rid, []).append((f"{pkey}.{rid}.C1", fn))
        # semi-continuous
        if cs.get("semi_continuous"):
            sc = cs["semi_continuous"]; rid = sc["rid"]
            fn = _semicontinuous_checker(sc["vars"], sc["min_batch"]); fn.__name__ = f"{pkey}_{rid}_sc"
            entries.setdefault(rid, []).append((f"{pkey}.{rid}.C1", fn))
        # domain from domain_int/domain_nonneg keys (P5,P9 used these)
        if cs.get("domain_int"):
            fn = _domain_checker(cs["domain_int"], "int"); fn.__name__ = f"{pkey}_int"
            entries.setdefault("R_dom_int", []).append((f"{pkey}.dom_int.C1", fn))
        if cs.get("domain_nonneg"):
            fn = _domain_checker(cs["domain_nonneg"], "nonneg"); fn.__name__ = f"{pkey}_nn"
            entries.setdefault("R_dom_nn", []).append((f"{pkey}.dom_nn.C1", fn))
        # objective coef + opt
        if cs.get("objective"):
            terms = [(v, c) for v, c in cs["objective"]["terms"]]
            fc = _obj_coef_checker(terms); fc.__name__ = f"{pkey}_obj_coef"
            fo = _obj_opt_checker(terms);  fo.__name__ = f"{pkey}_obj_opt"
            entries.setdefault("R_obj", []).append((f"{pkey}.obj.C1", fc))
            entries.setdefault("R_obj", []).append((f"{pkey}.obj.C2", fo))
        reg[pkey] = entries
    return reg

REGISTRY.update(_build_scaled_registry())