import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Decision variables (binary)
    sel_calculus = model.addVar(vtype=gp.GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=gp.GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=gp.GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=gp.GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=gp.GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=gp.GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=gp.GRB.BINARY, name="sel_fc")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    # Constraints
    # Math requirement: calculus + or + ds + bs + fc >= 2
    model.addConstr(sel_calculus + sel_or + sel_ds + sel_bs + sel_fc >= 2, name="math_req")

    # OR requirement: or + bs + cs + fc >= 2
    model.addConstr(sel_or + sel_bs + sel_cs + sel_fc >= 2, name="or_req")

    # Computer requirement: ds + cs + cp >= 2
    model.addConstr(sel_ds + sel_cs + sel_cp >= 2, name="comp_req")

    # Prerequisites
    # bs prerequisite for bs: bs <= calculus
    model.addConstr(sel_bs <= sel_calculus, name="bs_prereq")

    # CS and DS require CP
    model.addConstr(sel_cs <= sel_cp, name="cs_prereq")
    model.addConstr(sel_ds <= sel_cp, name="ds_prereq")

    # FC prerequisite for BS
    model.addConstr(sel_fc <= sel_bs, name="fc_prereq")

    # Objective: minimize total number of courses
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc, gp.GRB.MINIMIZE)

    return model, variables


def _status_to_string(status) -> str:
    if status == gp.GRB.OPTIMAL:
        return "OPTIMAL"
    if status == gp.GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    if status == gp.GRB.INFEASIBLE:
        return "INFEASIBLE"
    if status == gp.GRB.UNBOUNDED:
        return "UNBOUNDED"
    if status == gp.GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    return str(status)


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_str = _status_to_string(model.Status)
    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Read variable values
    sol = {
        "sel_calculus": int(round(variables["sel_calculus"].X)),
        "sel_or": int(round(variables["sel_or"].X)),
        "sel_ds": int(round(variables["sel_ds"].X)),
        "sel_bs": int(round(variables["sel_bs"].X)),
        "sel_cs": int(round(variables["sel_cs"].X)),
        "sel_cp": int(round(variables["sel_cp"].X)),
        "sel_fc": int(round(variables["sel_fc"].X)),
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": {
            "sel_calculus": sol["sel_calculus"],
            "sel_or": sol["sel_or"],
            "sel_ds": sol["sel_ds"],
            "sel_bs": sol["sel_bs"],
            "sel_cs": sol["sel_cs"],
            "sel_cp": sol["sel_cp"],
            "sel_fc": sol["sel_fc"]
        }
    }