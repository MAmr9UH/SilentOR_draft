import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Suppress solver output if possible
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

    # Decision variables
    variables = {}

    # Opening decisions
    for c in centers:
        key = f"y_{c}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Transportation variables
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Demand constraints: meet exactly the demand for each store
    for s in stores:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == demand[s], name=f"demand_{s}")

    # Capacity constraints: total shipped from a center cannot exceed its capacity if opened
    for c in centers:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for s in stores)
        model.addConstr(expr <= capacity[c] * variables[f"y_{c}"], name=f"cap_{c}")

    # Objective: minimize fixed opening costs + transportation costs
    obj = gp.quicksum(fixed_opening_cost[c] * variables[f"y_{c}"] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * variables[f"f_{c}_{s}"]

    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(status_int, str(status_int))

    objective = float(model.ObjVal)

    solution = {}
    # Y variables
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
    # f variables
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }