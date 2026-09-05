from gurobipy import GRB

def build_model(data: dict):
    from gurobipy import Model, GRB

    model = Model()

    # Decision variables (binary)
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = model.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Objective: minimize total number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)

    # Category quotas
    math_count = sel_calculus + sel_or + sel_ds + sel_ms + sel_fc
    or_count = sel_or + sel_ms + sel_cs + sel_fc
    comp_count = sel_ds + sel_cs + sel_cp

    model.addConstr(math_count >= 2, name="math_min2")
    model.addConstr(or_count >= 2, name="or_min2")
    model.addConstr(comp_count >= 2, name="comp_min2")

    # Prerequisites as implications
    # If a course is selected, its prerequisite must be selected
    model.addConstr(sel_cs <= sel_cp, name="cs_after_cp")
    model.addConstr(sel_ds <= sel_cp, name="ds_after_cp")
    model.addConstr(sel_ms <= sel_calculus, name="ms_after_calculus")
    model.addConstr(sel_fc <= sel_ms, name="fc_after_ms")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    model.update()
    objective_value = float(model.ObjVal)

    solution = {k: int(v.X) for k, v in variables.items()}

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }