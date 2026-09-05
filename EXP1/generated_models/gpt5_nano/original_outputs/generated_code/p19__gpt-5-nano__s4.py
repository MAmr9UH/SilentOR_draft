import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()
    try:
        model.setParam("OutputFlag", 0)
    except Exception:
        pass

    # Variables
    variables = {}

    # y_c (binary opening decisions)
    y = {}
    for c in centers:
        key = f"y_{c}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        y[c] = v
        variables[key] = v

    # f_c_s (shipping quantities)
    f = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, name=key)
            f[key] = v
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s == demand_s
    for s in stores:
        expr = gp.quicksum(f[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        expr = gp.quicksum(f[f"{c}_{s}"] for s in stores)
        model.addConstr(expr <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize fixed opening costs + transportation costs
    obj = gp.quicksum(opening_costs[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * f[f"{c}_{s}"]
    model.setObjective(obj, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal)

    solution = {k: float(v.X) for k, v in variables.items()}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }