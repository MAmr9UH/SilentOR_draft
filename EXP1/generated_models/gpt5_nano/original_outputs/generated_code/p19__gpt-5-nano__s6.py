import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("LogiSphere")
    model.Params.OutputFlag = 0  # silent solver

    # Decision variables
    variables = {}

    # Opening decisions y_c
    for c in centers:
        key = f"y_{c}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Shipments f_{c}_{s}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)

    model.update()

    # Objective: minimize total opening plus transportation costs
    obj = gp.LinExpr()
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    for c in centers:
        obj += opening_cost[c] * variables[f"y_{c}"]

    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * variables[f"f_{c}_{s}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    demand = data["demand"]
    capacity = data["capacity"]

    # Demand satisfaction at each store: sum_c f_{c,s} = demand_s
    for s in stores:
        model.addConstr(gp.quicksum(variables[f"f_{c}_{s}"] for c in centers) == demand[s],
                        name=f"demand_{s}")

    # Capacity constraints: for each center, sum_s f_{c,s} <= capacity[c] * y_c
    for c in centers:
        model.addConstr(gp.quicksum(variables[f"{c}_{s}"] for s in stores) <= capacity[c] * variables[f"y_{c}"],
                        name=f"cap_{c}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_val = model.Status
    if status_val == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_val == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_val == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_val == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_val == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_val)

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }