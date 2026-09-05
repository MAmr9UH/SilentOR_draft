import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("SupplyLink")

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}")

    # Parameters
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    capacity = data["capacity"]
    demand = data["demand"]

    # Constraints
    # Demand satisfaction
    for s in stores:
        model.addConstr(gp.quicksum(f[(c, s)] for c in centers) == demand[s], name=f"Dem_{s}")

    # Capacity (with opening decision)
    for c in centers:
        model.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Objective
    transport_term = gp.quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    opening_term = gp.quicksum(opening_costs[c] * y[c] for c in centers)
    model.setObjective(transport_term + opening_term, GRB.MINIMIZE)

    model.update()

    # Expose variables in a flat dictionary with exact keys
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

    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    else:
        status = str(st)

    objective = float(model.ObjVal)

    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }