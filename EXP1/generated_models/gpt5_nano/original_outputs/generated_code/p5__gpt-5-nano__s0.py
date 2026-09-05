from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    model = Model()
    # Decision variables
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Prerequisites
    model.addConstr(sel_bs <= sel_calculus)  # bsPrereq: calculus
    model.addConstr(sel_cs <= sel_cp)        # csPrereq: cp
    model.addConstr(sel_ds <= sel_cp)        # dsPrereq: cp
    model.addConstr(sel_fc <= sel_bs)        # fcPrereq: bs

    # Requirements:
    # Math: calculus, or, ds, bs, fc
    math_set = [sel_calculus, sel_or, sel_ds, sel_bs, sel_fc]
    # OR: or, bs, cs, fc
    or_set = [sel_or, sel_bs, sel_cs, sel_fc]
    # Computer: ds, cs, cp
    comp_set = [sel_ds, sel_cs, sel_cp]

    model.addConstr(quicksum(math_set) >= 2)
    model.addConstr(quicksum(or_set) >= 2)
    model.addConstr(quicksum(comp_set) >= 2)

    # Objective: minimize number of courses
    model.setObjective(quicksum([sel_calculus, sel_or, sel_ds, sel_bs, sel_cs, sel_cp, sel_fc]), GRB.MINIMIZE)

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    objective_val = float(model.ObjVal)

    def vval(key: str) -> int:
        v = variables[key]
        return int(round(v.X))

    solution = {
        "sel_calculus": vval("sel_calculus"),
        "sel_or": vval("sel_or"),
        "sel_ds": vval("sel_ds"),
        "sel_bs": vval("sel_bs"),
        "sel_cs": vval("sel_cs"),
        "sel_cp": vval("sel_cp"),
        "sel_fc": vval("sel_fc"),
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }