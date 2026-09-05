import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Optional: silence solver output
    try:
        model.setParam('OutputFlag', 0)
    except Exception:
        pass

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    # Objective: minimize total opening costs + transportation costs
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    objective = quicksum(opening_cost[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            objective += transport_cost[c][s] * f[c][s]

    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction: sum_c f_c_s = demand_s
    demand = data["demand"]
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    capacity = data["capacity"]
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    model.update()

    # Flatten variables into required keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to human-readable string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    objective_value = model.ObjVal

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": float(objective_value),
        "solution": solution
    }