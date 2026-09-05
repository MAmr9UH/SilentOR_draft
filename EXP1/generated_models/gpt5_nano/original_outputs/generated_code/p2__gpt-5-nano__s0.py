from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    m = Model("course_minimization")

    # Create binary decision variables for each course
    vars = {
        "sel_calculus": m.addVar(vtype=GRB.BINARY, name="sel_calculus"),
        "sel_or": m.addVar(vtype=GRB.BINARY, name="sel_or"),
        "sel_ds": m.addVar(vtype=GRB.BINARY, name="sel_ds"),
        "sel_ms": m.addVar(vtype=GRB.BINARY, name="sel_ms"),
        "sel_cs": m.addVar(vtype=GRB.BINARY, name="sel_cs"),
        "sel_cp": m.addVar(vtype=GRB.BINARY, name="sel_cp"),
        "sel_fc": m.addVar(vtype=GRB.BINARY, name="sel_fc")
    }

    m.update()

    # Prerequisites
    m.addConstr(vars["sel_ds"] <= vars["sel_cp"], name="prereq_ds")
    m.addConstr(vars["sel_cs"] <= vars["sel_cp"], name="prereq_cs")
    m.addConstr(vars["sel_ms"] <= vars["sel_calculus"], name="prereq_ms")
    m.addConstr(vars["sel_fc"] <= vars["sel_ms"], name="prereq_fc")

    # Category coverage constraints (at least 2 in each category)
    math_sum = quicksum([vars["sel_calculus"], vars["sel_or"], vars["sel_ds"], vars["sel_ms"], vars["sel_fc"]])
    or_sum = quicksum([vars["sel_or"], vars["sel_ms"], vars["sel_cs"], vars["sel_fc"]])
    comp_sum = quicksum([vars["sel_cp"], vars["sel_ds"], vars["sel_cs"]])

    m.addConstr(math_sum >= 2, name="math_ge2")
    m.addConstr(or_sum >= 2, name="or_ge2")
    m.addConstr(comp_sum >= 2, name="comp_ge2")

    # Objective: minimize total number of courses taken
    m.setObjective(quicksum([vars["sel_calculus"],
                               vars["sel_or"],
                               vars["sel_ds"],
                               vars["sel_ms"],
                               vars["sel_cs"],
                               vars["sel_cp"],
                               vars["sel_fc"]]), GRB.MINIMIZE)

    return m, vars

def solve(data: dict) -> dict:
    model, vars = build_model(data)
    model.optimize()

    stat = model.Status
    status_str = "UNKNOWN"
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"

    solution = {k: int(vars[k].X) for k in [
        "sel_calculus",
        "sel_or",
        "sel_ds",
        "sel_ms",
        "sel_cs",
        "sel_cp",
        "sel_fc",
    ]}

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }