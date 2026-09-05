import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Decision variables: integer number of workers per shift
    s1 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s4")

    model.update()

    # Objective: minimize total wage
    w = data["shift_wage"]
    model.setObjective(
        w["1"] * s1 + w["2"] * s2 + w["3"] * s3 + w["4"] * s4,
        GRB.MINIMIZE
    )

    # Coverage constraints
    required = data["workers_required_by_window"]  # length 8
    coverage = data["shift_coverage"]  # keys "1".."4" -> list of windows
    vars_map = {1: s1, 2: s2, 3: s3, 4: s4}

    for w in range(8):
        # Sum contributions from shifts that cover window w
        expr = gp.quicksum(vars_map[k] for k in range(1, 5) if w in coverage[str(k)])
        model.addConstr(expr >= required[w], name=f"cov_w{w}")

    variables = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
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

    objective = float(model.ObjVal)

    solution = {
        "s1": float(variables["s1"].X),
        "s2": float(variables["s2"].X),
        "s3": float(variables["s3"].X),
        "s4": float(variables["s4"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }