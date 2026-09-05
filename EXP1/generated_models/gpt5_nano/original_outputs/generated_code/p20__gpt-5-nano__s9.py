import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("distribution_network")

    # Decision variables
    variables = {}

    # Opening variables
    y_vars = {}
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y_vars[c] = var
        variables[f"y_{c}"] = var

    # Shipment variables
    f_vars = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            f_vars[(c, s)] = var
            variables[key] = var

    model.update()

    # Objective: minimize total opening + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_costs = data["transport_cost"]
    obj = quicksum(opening_costs[c] * y_vars[c] for c in centers) + \
          quicksum(transport_costs[c][s] * f_vars[(c, s)] for c in centers for s in stores)

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    demands = data["demand"]
    capacities = data["capacity"]

    # Demand satisfaction
    for s in stores:
        model.addConstr(quicksum(f_vars[(c, s)] for c in centers) == demands[s])

    # Capacity constraints with opening decision
    for c in centers:
        model.addConstr(quicksum(f_vars[(c, s)] for s in stores) <= capacities[c] * y_vars[c])

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
    status_int = model.Status
    status_str = status_map.get(status_int, str(status_int))

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }