from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    model = Model()
    # Course codes as per problem
    codes = ["calculus", "or", "ds", "ms", "cs", "cp", "fc"]

    # Decision variables: take course (binary)
    sel = {}
    for c in codes:
        sel[c] = model.addVar(vtype=GRB.BINARY, name=f"sel_{c}")

    # Time/order variables (integer 1..7)
    t = {}
    for c in codes:
        t[c] = model.addVar(vtype=GRB.INTEGER, lb=1, ub=7, name=f"t_{c}")

    model.update()

    # Category quotas
    # Math: calculus, or, ds, ms, fc -> exactly 2
    model.addConstr(sel["calculus"] + sel["or"] + sel["ds"] + sel["ms"] + sel["fc"] == 2, name="math_quota")
    # OR: or, ms, cs, fc -> exactly 2
    model.addConstr(sel["or"] + sel["ms"] + sel["cs"] + sel["fc"] == 2, name="or_quota")
    # Computer: ds, cs, cp -> exactly 2
    model.addConstr(sel["ds"] + sel["cs"] + sel["cp"] == 2, name="comp_quota")

    # Prerequisite gating (if course is taken, prerequisites must be taken)
    # MS requires calculus
    model.addConstr(sel["ms"] <= sel["calculus"], name="ms_prereq_calculus")
    # FC requires MS
    model.addConstr(sel["fc"] <= sel["ms"], name="fc_prereq_ms")
    # DS and CS require CP (prereq)
    model.addConstr(sel["ds"] <= sel["cp"], name="ds_prereq_cp")
    model.addConstr(sel["cs"] <= sel["cp"], name="cs_prereq_cp")

    # Temporal precedence (only active if the course is taken)
    M = 10  # big-M
    model.addConstr(t["ds"] >= t["cp"] + 1 - M * (1 - sel["ds"]), name="time_ds_after_cp")
    model.addConstr(t["cs"] >= t["cp"] + 1 - M * (1 - sel["cs"]), name="time_cs_after_cp")
    model.addConstr(t["ms"] >= t["calculus"] + 1 - M * (1 - sel["ms"]), name="time_ms_after_calculus")
    model.addConstr(t["fc"] >= t["ms"] + 1 - M * (1 - sel["fc"]), name="time_fc_after_ms")

    # Objective: minimize total number of courses taken
    model.setObjective(
        quicksum([sel[c] for c in codes]),
        GRB.MINIMIZE
    )

    model.update()

    variables = {
        "sel_calculus": sel["calculus"],
        "sel_or": sel["or"],
        "sel_ds": sel["ds"],
        "sel_ms": sel["ms"],
        "sel_cs": sel["cs"],
        "sel_cp": sel["cp"],
        "sel_fc": sel["fc"]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_value = float(model.ObjVal)

    sol = {
        "sel_calculus": int(variables["sel_calculus"].X + 0.5),
        "sel_or": int(variables["sel_or"].X + 0.5),
        "sel_ds": int(variables["sel_ds"].X + 0.5),
        "sel_ms": int(variables["sel_ms"].X + 0.5),
        "sel_cs": int(variables["sel_cs"].X + 0.5),
        "sel_cp": int(variables["sel_cp"].X + 0.5),
        "sel_fc": int(variables["sel_fc"].X + 0.5)
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": sol
    }