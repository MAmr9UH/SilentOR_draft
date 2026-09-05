import math
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = Model()
    # Optional: suppress solver output
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

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

    # Demand constraints: sum_c f[c][s] == demand[s]
    for s in stores:
        model.addConstr(quicksum(f[c][s] for c in centers) == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints: sum_s f[c][s] <= capacity[c] * y[c]
    for c in centers:
        model.addConstr(quicksum(f[c][s] for s in stores) <= data["capacity"][c] * y[c], name=f"cap_{c}")

    # Objective: minimize fixed opening costs + transport costs
    fixed_cost = quicksum(data["fixed_opening_cost"][c] * y[c] for c in centers)
    transport_cost = quicksum(data["transport_cost"][c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(fixed_cost + transport_cost, GRB.MINIMIZE)

    # Build variables dict with exact keys required
    variables = {}
    # y variables: y_c1, y_c2, y_c3, y_c4
    for idx, c in enumerate(['c1', 'c2', 'c3', 'c4'], start=1):
        variables[f"y_c{idx}"] = y[c]

    # f variables: f_cX_sY
    for c in ['c1', 'c2', 'c3', 'c4']:
        for s in ['s1','s2','s3','s4','s5','s6','s7','s8']:
            key = f"f_{c}_{s}"
            variables[key] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    objective = float(model.ObjVal)

    # Build solution dictionary with values of all variables
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }