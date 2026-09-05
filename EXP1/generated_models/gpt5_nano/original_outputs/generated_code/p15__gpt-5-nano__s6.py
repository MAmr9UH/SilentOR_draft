from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    model = Model()
    model.setParam('OutputFlag', 0)

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
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Objective
    model.setObjective(
        quicksum(opening_cost[c] * y[c] for c in centers) +
        quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores),
        GRB.MINIMIZE
    )

    # Demand constraints: sum_c f_{c,s} == demand_s
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Collect variables into flat dict with exact keys
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

    # Status string
    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(status_num)

    model.update()
    obj = model.ObjVal

    keys = [
        "y_c1","y_c2","y_c3","y_c4","y_c5",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5","f_c1_s6","f_c1_s7",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5","f_c2_s6","f_c2_s7",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5","f_c3_s6","f_c3_s7",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5","f_c4_s6","f_c4_s7",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4","f_c5_s5","f_c5_s6","f_c5_s7"
    ]
    solution_vals = {}
    for k in keys:
        solution_vals[k] = float(variables[k].X)

    return {
        "status": status_str,
        "objective": float(obj),
        "solution": solution_vals
    }