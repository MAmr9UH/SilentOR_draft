import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = model.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    # Objective function: Minimize the number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)

    # Constraints: Take two math courses
    model.addConstr(sel_calculus + sel_or + sel_ms + sel_fc >= 2, "math_courses")

    # Constraints: Take two operations research courses
    model.addConstr(sel_or + sel_ms + sel_cs + sel_fc >= 2, "or_courses")

    # Constraints: Take two computer courses
    model.addConstr(sel_ds + sel_cp + sel_cs >= 2, "computer_courses")

    # Prerequisites: computer simulation or data structures must be taken after computer programming
    model.addConstr(sel_cs + sel_ds <= sel_cp + 1, "prereq_cs_ds_after_cp")

    # Prerequisites: management statistics must be taken after calculus
    model.addConstr(sel_ms <= sel_calculus + 1, "prereq_ms_after_calculus")

    # Prerequisites: forecasting must be taken after management statistics
    model.addConstr(sel_fc <= sel_ms + 1, "prereq_fc_after_ms")

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_ms": sel_ms,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "sel_calculus": float(variables["sel_calculus"].X),
        "sel_or": float(variables["sel_or"].X),
        "sel_ds": float(variables["sel_ds"].X),
        "sel_ms": float(variables["sel_ms"].X),
        "sel_cs": float(variables["sel_cs"].X),
        "sel_cp": float(variables["sel_cp"].X),
        "sel_fc": float(variables["sel_fc"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }