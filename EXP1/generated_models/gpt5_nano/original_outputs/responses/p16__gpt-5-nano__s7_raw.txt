import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for c in centers:
        y[c] = m.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    m.update()

    # Objective: minimize opening costs + transportation costs
    opening_term = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    m.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Demand constraints: meet exact demand for each store
    for s in stores:
        m.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: can't ship more than capacity if center is opened
    for c in centers:
        m.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Collect variables into a flat dict with keys exactly as required
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    objective_value = float(model.ObjVal)

    order = [
        "y_c1","y_c2","y_c3","y_c4","y_c5","y_c6","y_c7",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4",
        "f_c6_s1","f_c6_s2","f_c6_s3","f_c6_s4",
        "f_c7_s1","f_c7_s2","f_c7_s3","f_c7_s4",
    ]

    solution = {}
    for key in order:
        solution[key] = float(variables[key].X)

    return {"status": status_str, "objective": objective_value, "solution": solution}