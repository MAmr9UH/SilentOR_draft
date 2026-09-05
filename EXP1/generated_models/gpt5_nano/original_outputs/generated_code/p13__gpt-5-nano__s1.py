from gurobipy import *

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    m = Model()

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

    # Demand constraints: sum_c f[c][s] == demand[s]
    for s in stores:
        m.addConstr(quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f[c][s] <= capacity[c] * y[c]
    for c in centers:
        m.addConstr(quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    obj = quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * f[c][s]
    m.setObjective(obj, GRB.MINIMIZE)

    # Build the required flat variables dictionary
    variables = {
        "y_c1": y["c1"],
        "y_c2": y["c2"],
        "y_c3": y["c3"],
        "y_c4": y["c4"],
        "f_c1_s1": f["c1"]["s1"],
        "f_c1_s2": f["c1"]["s2"],
        "f_c1_s3": f["c1"]["s3"],
        "f_c1_s4": f["c1"]["s4"],
        "f_c1_s5": f["c1"]["s5"],
        "f_c1_s6": f["c1"]["s6"],
        "f_c2_s1": f["c2"]["s1"],
        "f_c2_s2": f["c2"]["s2"],
        "f_c2_s3": f["c2"]["s3"],
        "f_c2_s4": f["c2"]["s4"],
        "f_c2_s5": f["c2"]["s5"],
        "f_c2_s6": f["c2"]["s6"],
        "f_c3_s1": f["c3"]["s1"],
        "f_c3_s2": f["c3"]["s2"],
        "f_c3_s3": f["c3"]["s3"],
        "f_c3_s4": f["c3"]["s4"],
        "f_c3_s5": f["c3"]["s5"],
        "f_c3_s6": f["c3"]["s6"],
        "f_c4_s1": f["c4"]["s1"],
        "f_c4_s2": f["c4"]["s2"],
        "f_c4_s3": f["c4"]["s3"],
        "f_c4_s4": f["c4"]["s4"],
        "f_c4_s5": f["c4"]["s5"],
        "f_c4_s6": f["c4"]["s6"],
    }

    return m, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Ensure up-to-date values
    model.update()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        val = var.X
        if val is None:
            val = 0.0
        solution[key] = float(val)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }