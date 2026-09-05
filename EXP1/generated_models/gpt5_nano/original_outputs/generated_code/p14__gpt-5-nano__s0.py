import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1", ..., "s8"]

    capacity = data["capacity"]            # dict: {"c1": ..., ...}
    demand = data["demand"]                # dict: {"s1": ..., ...}
    fixed_opening_cost = data["fixed_opening_cost"]  # dict: {"c1": ..., ...}
    transport_cost = data["transport_cost"]          # nested dict: {"c1": {"s1": ..., ...}, ...}

    # Decision variables
    y = {}  # whether to open center c
    for idx, c in enumerate(centers, start=1):
        y[c] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    f = {}  # flow from center c to store s
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = gp.quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    transport_cost_term = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_cost_term + transport_cost_term, gp.GRB.MINIMIZE)

    # Constraints
    # 1) Center capacity: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # 2) Demand satisfaction: sum_c f_c_s >= demand_s
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) >= demand[s], name=f"dem_{s}")

    # Prepare the flat variables dictionary to return
    variables = {}

    # y variables: keys y_c1, y_c2, ...
    for idx, c in enumerate(centers, start=1):
        key = f"y_c{idx}"
        variables[key] = y[c]

    # f variables: keys f_c1_s1, f_c1_s2, ..., f_c4_s8
    for idx_c, c in enumerate(centers, start=1):
        for idx_s, s in enumerate(stores, start=1):
            key = f"f_c{idx_c}_s{idx_s}"
            variables[key] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    if st == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_value = float(model.ObjVal)

    # Build solution dictionary with all required keys
    solution = {}

    centers = data["centers"]
    stores = data["stores"]

    # y variables
    for idx, c in enumerate(centers, start=1):
        solution[f"y_c{idx}"] = float(variables[f"y_c{idx}"].X)

    # f variables
    for idx_c, c in enumerate(centers, start=1):
        for idx_s, s in enumerate(stores, start=1):
            solution[f"f_c{idx_c}_s{idx_s}"] = float(variables[f"f_c{idx_c}_s{idx_s}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }