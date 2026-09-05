import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Variables
    variables = {}

    # Opening decision variables y_c1 ... y_c7
    y = {}
    for i, c in enumerate(centers, start=1):
        key = f"y_c{i}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        y[c] = v
        variables[key] = v

    # Transportation variables f_c_s
    f_vars = {}
    for i, c in enumerate(centers, start=1):
        f_vars[c] = {}
        for j, s in enumerate(stores, start=1):
            key = f"f_{c}_{s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            f_vars[c][s] = v
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s = demand_s
    for s in stores:
        model.addConstr(gp.quicksum(f_vars[c][s] for c in centers) == demand[s], name=f"Demand_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(f_vars[c][s] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Objective: minimize opening costs + transportation costs
    obj_open = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    obj_trans = gp.quicksum(transport_cost[c][s] * f_vars[c][s] for c in centers for s in stores)
    model.setObjective(obj_open + obj_trans, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_str = "UNKNOWN"
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    keys = [
        "y_c1","y_c2","y_c3","y_c4","y_c5","y_c6","y_c7",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4",
        "f_c6_s1","f_c6_s2","f_c6_s3","f_c6_s4",
        "f_c7_s1","f_c7_s2","f_c7_s3","f_c7_s4"
    ]

    solution = {}
    for k in keys:
        solution[k] = float(variables[k].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }