import sys
from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    codes = ["calculus", "or", "ds", "bs", "cs", "cp", "fc"]
    model = Model()
    model.setParam("OutputFlag", 0)

    # Create binary decision variables for each course
    vars_by_code = {code: model.addVar(vtype=GRB.BINARY, name=f"sel_{code}") for code in codes}
    model.update()

    # Constraints
    # Math >= 2: calculus, or, ds, bs, fc
    model.addConstr(quicksum(vars_by_code[c] for c in ["calculus", "or", "ds", "bs", "fc"]) >= 2, name="math_min2")
    # OR >= 2: or, bs, cs, fc
    model.addConstr(quicksum(vars_by_code[c] for c in ["or", "bs", "cs", "fc"]) >= 2, name="or_min2")
    # Computer >= 2: ds, cs, cp
    model.addConstr(quicksum(vars_by_code[c] for c in ["ds", "cs", "cp"]) >= 2, name="comp_min2")

    # Prerequisites
    model.addConstr(vars_by_code["bs"] <= vars_by_code["calculus"])  # bs requires calculus
    model.addConstr(vars_by_code["ds"] <= vars_by_code["cp"])          # ds requires cp
    model.addConstr(vars_by_code["cs"] <= vars_by_code["cp"])          # cs requires cp
    model.addConstr(vars_by_code["fc"] <= vars_by_code["bs"])          # fc requires bs

    # Objective: minimize total number of courses
    model.setObjective(quicksum(vars_by_code[c] for c in codes), GRB.MINIMIZE)

    variables = {
        "sel_calculus": vars_by_code["calculus"],
        "sel_or": vars_by_code["or"],
        "sel_ds": vars_by_code["ds"],
        "sel_bs": vars_by_code["bs"],
        "sel_cs": vars_by_code["cs"],
        "sel_cp": vars_by_code["cp"],
        "sel_fc": vars_by_code["fc"],
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))
    objective = float(model.ObjVal)

    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_bs": int(variables["sel_bs"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }