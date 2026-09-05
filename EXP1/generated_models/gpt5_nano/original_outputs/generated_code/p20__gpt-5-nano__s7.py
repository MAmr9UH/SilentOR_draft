import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
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
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Demand constraints: for each store, total received equals its demand
    for s in stores:
        model.addConstr(quicksum(f[(c, s)] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: shipments from a center cannot exceed capacity if opened
    for c in centers:
        model.addConstr(quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs plus transportation costs
    total_open_cost = quicksum(opening_cost[c] * y[c] for c in centers)
    total_transport_cost = quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(total_open_cost + total_transport_cost, GRB.MINIMIZE)

    # Prepare variables dict to return with exact keys
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

    # Status string
    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(st)

    objective = float(model.ObjVal)

    # Build solution dictionary in the required variable order
    keys_ordered = [
        "y_c1","y_c2","y_c3","y_c4","y_c5","y_c6","y_c7",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4","f_c5_s5",
        "f_c6_s1","f_c6_s2","f_c6_s3","f_c6_s4","f_c6_s5",
        "f_c7_s1","f_c7_s2","f_c7_s3","f_c7_s4","f_c7_s5"
    ]

    solution = {}
    for key in keys_ordered:
        solution[key] = variables[key].X

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }