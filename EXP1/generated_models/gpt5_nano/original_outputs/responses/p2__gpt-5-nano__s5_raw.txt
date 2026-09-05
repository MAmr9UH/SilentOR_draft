import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    courses = data.get("courses", [])
    N = len(courses)

    m = gp.Model("course_selection")

    # Decision variables: sel_<code> for each course
    codes = ["calculus", "or", "ds", "ms", "cs", "cp", "fc"]
    code_to_var = {}
    for code in codes:
        if code in courses:
            code_to_var[code] = m.addVar(vtype=GRB.BINARY, name=f"sel_{code}")
        else:
            code_to_var[code] = None  # Should not happen for provided data

    # Position variables for possible sequencing (1..N)
    pos = {}
    for code in courses:
        pos[code] = m.addVar(vtype=GRB.INTEGER, lb=1, ub=N, name=f"pos_{code}")

    # Objective: minimize total number of courses taken
    m.setObjective(gp.quicksum(code_to_var[code] for code in codes if code in courses), GRB.MINIMIZE)

    # Prerequisites (with Big-M to activate only when both courses are selected)
    M = N + 5  # a safe big-M

    # computer simulation (cs) or data structures (ds) must be after computer programming (cp)
    m.addConstr(pos["cs"] >= pos["cp"] + 1 - M * (1 - code_to_var["cs"]) - M * (1 - code_to_var["cp"]))
    m.addConstr(pos["ds"] >= pos["cp"] + 1 - M * (1 - code_to_var["ds"]) - M * (1 - code_to_var["cp"]))

    # management statistics (ms) must be after calculus
    m.addConstr(pos["ms"] >= pos["calculus"] + 1 - M * (1 - code_to_var["ms"]) - M * (1 - code_to_var["calculus"]))

    # forecasting (fc) must be after management statistics
    m.addConstr(pos["fc"] >= pos["ms"] + 1 - M * (1 - code_to_var["fc"]) - M * (1 - code_to_var["ms"]))

    # Category constraints
    # Math: calculus, or, ds, ms, fc
    m.addConstr(code_to_var["calculus"] + code_to_var["or"] + code_to_var["ds"] + code_to_var["ms"] + code_to_var["fc"] >= 2)

    # Operations Research (OR): or, ms, cs, fc
    m.addConstr(code_to_var["or"] + code_to_var["ms"] + code_to_var["cs"] + code_to_var["fc"] >= 2)

    # Computer: cp, ds, cs
    m.addConstr(code_to_var["cp"] + code_to_var["ds"] + code_to_var["cs"] >= 2)

    m.update()

    variables = {
        "sel_calculus": code_to_var["calculus"],
        "sel_or": code_to_var["or"],
        "sel_ds": code_to_var["ds"],
        "sel_ms": code_to_var["ms"],
        "sel_cs": code_to_var["cs"],
        "sel_cp": code_to_var["cp"],
        "sel_fc": code_to_var["fc"],
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_str = None
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal) if model.ObjVal is not None else float('nan')

    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_ms": int(variables["sel_ms"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }