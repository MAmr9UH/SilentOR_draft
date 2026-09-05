import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build the forest of a capacitated facility location with transportation.
    Returns the model and a dict of all decision variables with exact keys as required.
    """
    model = gp.Model()

    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1","s2","s3","s4","s5","s6"]

    # Decision variables
    y_vars = {}
    for c in centers:
        y_vars[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f_vars = {}
    for c in centers:
        f_vars[c] = {}
        for s in stores:
            f_vars[c][s] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    capacity = data["capacity"]
    demand = data["demand"]

    obj = gp.quicksum(opening_costs[c] * y_vars[c] for c in centers) \
        + gp.quicksum(transport_cost[c][s] * f_vars[c][s] for c in centers for s in stores)

    model.setObjective(obj, GRB.MINIMIZE)

    # Demand constraints: meet each store's demand exactly
    for s in stores:
        model.addConstr(gp.quicksum(f_vars[c][s] for c in centers) == demand[s], name=f"Dem_{s}")

    # Capacity constraints: shipments from a center limited by capacity if opened
    for c in centers:
        model.addConstr(gp.quicksum(f_vars[c][s] for s in stores) <= capacity[c] * y_vars[c], name=f"Cap_{c}")

    # Assemble the flat variables dictionary with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y_vars[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f_vars[c][s]

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

    objective = model.ObjVal

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }