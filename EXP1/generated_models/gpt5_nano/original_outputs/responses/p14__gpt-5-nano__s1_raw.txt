from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = Model()

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

    # Objective: minimize total opening cost + transportation cost
    opening_term = quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Constraints
    # 1. Demand satisfaction
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # 2. Capacity with fixed charge linkage
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Prepare flattened variables dict to return
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

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_name = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    # Collect solution values in the exact keys required
    order = [
        "y_c1","y_c2","y_c3","y_c4",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5","f_c1_s6","f_c1_s7","f_c1_s8",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5","f_c2_s6","f_c2_s7","f_c2_s8",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5","f_c3_s6","f_c3_s7","f_c3_s8",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5","f_c4_s6","f_c4_s7","f_c4_s8"
    ]
    solution = {}
    for key in order:
        solution[key] = variables[key].X

    return {
        "type": "object",
        "status": status_name,
        "objective": objective,
        "solution": solution
    }