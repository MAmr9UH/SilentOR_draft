import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening = data["fixed_opening_cost"]
    transport = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # y_c: center open binary
    y = {}
    for c in centers:
        key = f"y_{c}"
        var = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = var
        y[c] = var

    # f_{c}_{s}: flow from center c to store s
    f = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = var
            f[(c, s)] = var

    model.update()

    # Objective: minimize closing cost + transportation cost
    opening_cost = gp.quicksum(f[(c, s)] * transport[c][s] for c in centers for s in stores)
    opening_cost += gp.quicksum(y[c] * fixed_opening[c] for c in centers)
    model.setObjective(opening_cost, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for s in stores:
        model.addConstr(gp.quicksum(f[(c, s)] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints
    for c in centers:
        model.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))
    objective_value = float(model.ObjVal)

    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }