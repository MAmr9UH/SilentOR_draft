import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(opening_costs[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * f[c][s]
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"Dem_{s}")

    # Capacity with opening indicator
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Export the variables dictionary with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    model.update()
    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CUTOFF: "CUTOFF",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        GRB.NODE_LIM: "NODE_LIM",
    }.get(st, str(st))

    objective_value = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }