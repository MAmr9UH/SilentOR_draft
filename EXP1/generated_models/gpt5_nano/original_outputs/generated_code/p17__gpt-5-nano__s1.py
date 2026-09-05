import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    centers = data["centers"]
    stores = data["stores"]

    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    variables = {}

    # Decision variables: y_c for opening centers
    for c in centers:
        key = f"y_{c}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Decision variables: f_c_s for shipments from center c to store s
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s == demand_s for each store s
    for s in stores:
        model.addConstr(quicksum(variables[f"f_{c}_{s}"] for c in centers) == demand[s])

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c for each center c
    for c in centers:
        model.addConstr(quicksum(variables[f"f_{c}_{s}"] for s in stores) <= capacity[c] * variables[f"y_{c}"])

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = quicksum(fixed_opening_cost[c] * variables[f"y_{c}"] for c in centers)
    transport_cost_term = quicksum(transport_cost[c][s] * variables[f"f_{c}_{s}"] for c in centers for s in stores)
    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

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
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Build solution dictionary with exact keys
    solution = {}

    centers = data["centers"]
    stores = data["stores"]

    for c in centers:
        key = f"y_{c}"
        solution[key] = float(variables[key].X)

    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    result = {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result