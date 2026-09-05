import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Suppress solver output for cleaner runs
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

    # Retrieve data-driven minima with safe fallbacks
    min_A = data.get("min_A", 240)
    min_B = data.get("min_B", 80)
    min_C = data.get("min_C", 120)

    # Costs
    freight_A = data.get("freight_cost", {}).get("A", 200)
    freight_B = data.get("freight_cost", {}).get("B", 160)

    # Decision variables
    trucks_A = model.addVar(vtype=GRB.INTEGER, name="trucks_A", lb=0)
    trucks_B = model.addVar(vtype=GRB.INTEGER, name="trucks_B", lb=0)

    # Constraints based on per-truck contents
    model.addConstr(4 * trucks_A + 7 * trucks_B >= min_A, name="A_min")
    model.addConstr(2 * trucks_A + 2 * trucks_B >= min_B, name="B_min")
    model.addConstr(6 * trucks_A + 2 * trucks_B >= min_C, name="C_min")

    # Objective: minimize total freight cost
    model.setObjective(freight_A * trucks_A + freight_B * trucks_B, GRB.MINIMIZE)

    model.update()

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    objective_value = model.ObjVal
    if objective_value is None:
        objective_value = 0.0

    trucks_A_val = int(variables["trucks_A"].X)
    trucks_B_val = int(variables["trucks_B"].X)

    solution = {
        "trucks_A": trucks_A_val,
        "trucks_B": trucks_B_val
    }

    return {
        "status": status_str,
        "objective": float(objective_value),
        "solution": solution
    }