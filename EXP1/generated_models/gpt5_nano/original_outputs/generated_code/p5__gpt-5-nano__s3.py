import sys
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    # Create model
    model = Model()

    # Decision variables (binary)
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")

    model.update()

    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }

    # Read minimum requirements from data (with sensible defaults)
    min_math = int(data.get("min_math", 2))
    min_or = int(data.get("min_or", 2))
    min_comp = int(data.get("min_comp", 2))

    # Contribution constraints
    math_count = quicksum([sel_calculus, sel_or, sel_ds, sel_bs, sel_fc])
    or_count = quicksum([sel_or, sel_bs, sel_cs, sel_fc])
    comp_count = quicksum([sel_ds, sel_cs, sel_cp])

    model.addConstr(math_count >= min_math, name="math_need")
    model.addConstr(or_count >= min_or, name="or_need")
    model.addConstr(comp_count >= min_comp, name="computer_need")

    # Prerequisites
    # Calculus is prerequisite for business statistics
    model.addConstr(sel_bs <= sel_calculus, name="prereq_bs_calculus")
    # Introduction to programming is prerequisite for cs and ds
    model.addConstr(sel_cs <= sel_cp, name="prereq_cs_cp")
    model.addConstr(sel_ds <= sel_cp, name="prereq_ds_cp")
    # Business statistics prerequisite for forecasting
    model.addConstr(sel_fc <= sel_bs, name="prereq_fc_bs")

    # Objective: minimize total number of courses
    model.setObjective(quicksum([sel_calculus, sel_or, sel_ds, sel_bs, sel_cs, sel_cp, sel_fc]), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(status_code, str(status_code))

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
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }