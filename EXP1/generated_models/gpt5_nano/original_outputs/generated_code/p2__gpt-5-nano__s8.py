import gurobipy as gp

def build_model(data: dict) -> tuple:
    m = gp.Model()
    # Create binary decision variables for each course
    sel_calculus = m.addVar(vtype=gp.GRB.BINARY, name="sel_calculus")
    sel_or = m.addVar(vtype=gp.GRB.BINARY, name="sel_or")
    sel_ds = m.addVar(vtype=gp.GRB.BINARY, name="sel_ds")
    sel_ms = m.addVar(vtype=gp.GRB.BINARY, name="sel_ms")
    sel_cs = m.addVar(vtype=gp.GRB.BINARY, name="sel_cs")
    sel_cp = m.addVar(vtype=gp.GRB.BINARY, name="sel_cp")
    sel_fc = m.addVar(vtype=gp.GRB.BINARY, name="sel_fc")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    # Category constraints
    # Math: calculus, ds, ms, fc
    m.addConstr(sel_calculus + sel_ds + sel_ms + sel_fc >= 2, name="math_count_ge_2")
    # Operations Research (OR): or, ms, cs, fc
    m.addConstr(sel_or + sel_ms + sel_cs + sel_fc >= 2, name="or_count_ge_2")
    # Computer: ds, cs, cp
    m.addConstr(sel_ds + sel_cs + sel_cp >= 2, name="computer_count_ge_2")

    # Prerequisites (take the course implies prerequisites are taken)
    m.addConstr(sel_ms <= sel_calculus, name="ms_after_calculus")
    m.addConstr(sel_ds <= sel_cp, name="ds_after_cp")
    m.addConstr(sel_cs <= sel_cp, name="cs_after_cp")
    m.addConstr(sel_fc <= sel_ms, name="fc_after_ms")

    # Objective: minimize total number of courses taken
    m.setObjective(sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc, gp.GRB.MINIMIZE)

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
        gp.GRB.INTERrupted if hasattr(gp.GRB, 'INTERRUPTED') else None: "INTERRUPTED",
        gp.GRB.INTERRUPTED: "INTERRUPTED",
        gp.GRB.CUTOFF: "CUTOFF",
        gp.GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        None: str(status_code)
    }
    status_str = status_map.get(status_code, str(status_code))

    obj_value = model.ObjVal

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
        "type": "object",
        "status": status_str,
        "objective": float(obj_value),
        "solution": solution
    }