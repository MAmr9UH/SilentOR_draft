import gurobipy as gp

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    m = gp.Model()

    # Decision variables
    y = {}
    for idx, c in enumerate(centers, start=1):
        y[c] = m.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    m.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.quicksum(opening_costs[c] * y[c] for c in centers) \
        + gp.quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    m.setObjective(obj, gp.GRB.MINIMIZE)

    # Demand constraints: meet exactly the demand at each store
    demand = data["demand"]
    for s in stores:
        m.addConstr(gp.quicksum(f[(c, s)] for c in centers) == demand[s], name=f"Dem_{s}")

    # Capacity constraints: sum shipments from a center <= capacity * y(center)
    capacity = data["capacity"]
    for c in centers:
        m.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Collect variables into a flat dict with exact keys expected by the caller
    variables = {}
    for idx, c in enumerate(centers, start=1):
        variables[f"y_c{idx}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
    }
    status_int = model.Status
    status_str = status_map.get(status_int, str(status_int))

    objective_value = float(model.ObjVal)

    # Build solution vector with all required keys
    centers = data["centers"]
    stores = data["stores"]

    solution = {}
    for idx, c in enumerate(centers, start=1):
        solution[f"y_c{idx}"] = float(variables[f"y_{c}"].X)

    for c in centers:
        for s in stores:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }