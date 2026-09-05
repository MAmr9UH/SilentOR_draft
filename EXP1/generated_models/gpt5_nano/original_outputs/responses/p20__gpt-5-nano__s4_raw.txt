import gurobipy as gp

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    shipments = {}
    for c in centers:
        for s in stores:
            shipments[(c, s)] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Constraints
    # Demand satisfaction: sum_c f_c_s == demand_s for all s
    for s in stores:
        model.addConstr(gp.quicksum(shipments[(c, s)] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c for all c
    for c in centers:
        model.addConstr(gp.quicksum(shipments[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: fixed opening costs + transportation costs
    open_cost = gp.quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    trans_cost = gp.quicksum(transport_cost[c][s] * shipments[(c, s)] for c in centers for s in stores)
    model.setObjective(open_cost + trans_cost, gp.GRB.MINIMIZE)

    # Prepare flat dictionary of variables to return
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = shipments[(c, s)]

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    if status_num == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_num == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_num == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_num == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_num == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_num)

    objective = model.ObjVal

    # Build solution dictionary with all keys in fixed order
    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = variables[f"y_{c}"].X
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = variables[f"f_{c}_{s}"].X

    return {
        "status": status,
        "objective": float(objective),
        "solution": solution
    }