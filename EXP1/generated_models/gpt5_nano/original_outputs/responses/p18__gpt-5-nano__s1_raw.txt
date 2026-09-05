import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    # Decision variables
    y = {}
    for c in centers:
        key = f"y_{c}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            f[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    model.update()

    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Demand constraints: sum_c f_c_s = demand_s
    for s in stores:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for s in stores) <= capacity[c] * y[f"y_{c}"], name=f"cap_{c}")

    # Objective: minimize opening + transportation costs
    obj = gp.quicksum(opening_cost[c] * y[f"y_{c}"] for c in centers) + gp.quicksum(
        transport_cost[c][s] * f[f"{c}_{s}"] for c in centers for s in stores
    )
    model.setObjective(obj, GRB.MINIMIZE)

    # Build and return variables dictionary with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[f"y_{c}"]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[f"{c}_{s}"]

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

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    objective_value = model.ObjVal

    return {
        "type": "object",
        "status": status_str,
        "objective": float(objective_value),
        "solution": solution
    }