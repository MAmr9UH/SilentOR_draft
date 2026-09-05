import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Objective: min opening costs + transportation costs
    opening_term = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Demand constraints: sum_c f_{c,s} == demand_s
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"capacity_{c}")

    # Prepare return dictionary of variables with exact keys
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

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD"
    }
    st = model.Status
    status_str = status_map.get(st, str(st))

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }