import gurobipy as gp

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
        y[c] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Demand constraints: meet exactly the demand for each store
    for s in stores:
        model.addConstr(gp.quicksum(f[(c, s)] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: shipments from a center cannot exceed capacity if opened
    for c in centers:
        model.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_total = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_total = gp.quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_total + transport_total, gp.GRB.MINIMIZE)

    # Bundle variables into the exact expected keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }