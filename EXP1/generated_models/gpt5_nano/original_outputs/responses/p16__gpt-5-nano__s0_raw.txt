import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}")

    model.update()

    # Objective: Minimize opening costs + transportation costs
    obj = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * f[c][s]
    model.setObjective(obj, GRB.MINIMIZE)

    # Demand constraints: meet demand at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"Dem_{s}")

    # Capacity constraints: do not ship more than capacity if opened
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Gather variables into a flat dictionary with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    objective_value = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }