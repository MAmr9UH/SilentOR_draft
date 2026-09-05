import gurobipy as gp
from gurobipy import GRB
from typing import Tuple, Dict

def build_model(data: dict) -> Tuple[gp.Model, Dict[str, gp.Var]]:
    # Create model
    model = gp.Model()

    # Decision variables: binary indicators for taking each course
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_ms = model.addVar(vtype=GRB.BINARY, name="sel_ms")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    model.update()

    # Category constraints (exactly 2 per category)
    # Math: calculus, or, ds, ms, fc
    model.addConstr(sel_calculus + sel_or + sel_ds + sel_ms + sel_fc == 2, name="math_count")
    # OR: or, ms, cs, fc
    model.addConstr(sel_or + sel_ms + sel_cs + sel_fc == 2, name="or_count")
    # Computer: ds, cs, cp
    model.addConstr(sel_ds + sel_cs + sel_cp == 2, name="computer_count")

    # Prerequisites:
    # ds or cs requires cp
    model.addConstr(sel_ds <= sel_cp, name="prereq_ds_cp")
    model.addConstr(sel_cs <= sel_cp, name="prereq_cs_cp")
    # ms requires cal
    model.addConstr(sel_ms <= sel_calculus, name="prereq_ms_calculus")
    # fc requires ms (and thus calculus via transitive)
    model.addConstr(sel_fc <= sel_ms, name="prereq_fc_ms")

    # Objective: minimize total number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_ms + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)

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

    # Interpret status
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    # Ensure we fetch updated values
    model.update()

    objective = float(model.ObjVal)

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
        "status": status,
        "objective": objective,
        "solution": solution
    }