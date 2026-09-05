import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Decision variables: 1 if course is taken
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    model.update()

    # Objective: minimize total number of courses taken
    model.setObjective(
        sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc,
        GRB.MINIMIZE
    )

    # Thresholds (default to 2, but allow override from data if provided)
    math_req = 2
    or_req = 2
    comp_req = 2
    if isinstance(data, dict):
        reqs = data.get("requirements", {})
        math_req = reqs.get("math", math_req)
        or_req = reqs.get("or", or_req)
        comp_req = reqs.get("computer", comp_req)

    # Math requirement: calculus, or, ds, bs, fc contribute to math
    math_contrib = sel_calculus + sel_or + sel_ds + sel_bs + sel_fc
    model.addConstr(math_contrib >= math_req, name="math_req")

    # OR requirement: or, bs, cs, fc contribute to OR
    or_contrib = sel_or + sel_bs + sel_cs + sel_fc
    model.addConstr(or_contrib >= or_req, name="or_req")

    # Computer requirement: ds, cs, cp contribute to computer
    comp_contrib = sel_ds + sel_cs + sel_cp
    model.addConstr(comp_contrib >= comp_req, name="comp_req")

    # Prerequisites
    model.addConstr(sel_bs <= sel_calculus, name="pr_bs_calculus")
    model.addConstr(sel_cs <= sel_cp, name="pr_cs_cp")
    model.addConstr(sel_ds <= sel_cp, name="pr_ds_cp")
    model.addConstr(sel_fc <= sel_bs, name="pr_fc_bs")

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

    status_code = model.Status
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

    # Read solution values
    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_bs": int(variables["sel_bs"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }

    result = {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result