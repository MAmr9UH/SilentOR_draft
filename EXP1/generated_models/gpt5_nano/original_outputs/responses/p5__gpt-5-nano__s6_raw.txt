import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    m = gp.Model("BasketweaversMajor")

    # Decision variables
    sel_calculus = m.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = m.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = m.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = m.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = m.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = m.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = m.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Objective: minimize number of courses taken
    m.setObjective(
        sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc,
        GRB.MINIMIZE
    )

    # Requirements
    math_sum = sel_calculus + sel_ds + sel_bs + sel_fc
    m.addConstr(math_sum >= 2, name="math_min2")

    or_sum = sel_or + sel_bs + sel_cs + sel_fc
    m.addConstr(or_sum >= 2, name="or_min2")

    comp_sum = sel_ds + sel_cs + sel_cp
    m.addConstr(comp_sum >= 2, name="comp_min2")

    # Prerequisites
    m.addConstr(sel_bs <= sel_calculus, name="bs_requires_calculus")
    m.addConstr(sel_cs <= sel_cp, name="cs_requires_cp")
    m.addConstr(sel_ds <= sel_cp, name="ds_requires_cp")
    m.addConstr(sel_fc <= sel_bs, name="fc_requires_bs")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

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
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else 0.0,
        "solution": solution
    }

    return result