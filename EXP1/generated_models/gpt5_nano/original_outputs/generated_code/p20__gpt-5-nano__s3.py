import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model("DC_Optimization")

    # Decision Variables
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Demand constraints: sum over centers of shipments to store s equals demand[s]
    for s in stores:
        model.addConstr(quicksum(f[(c, s)] for c in centers) == demand[s], name=f"Demand_{s}")

    # Capacity constraints: sum over stores of shipments from center c <= capacity[c] * y_c
    for c in centers:
        model.addConstr(quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"Cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = quicksum(opening_cost[c] * y[c] for c in centers)
    transport_cost_term = quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

    # Prepare variables dict with exact keys
    variables = {}
    for idx, c in enumerate(centers, start=1):
        variables[f"y_c{idx}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

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
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }