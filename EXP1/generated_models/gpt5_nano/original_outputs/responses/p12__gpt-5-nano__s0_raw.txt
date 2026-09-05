def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB, quicksum

    centers = data["centers"]
    stores = data["stores"]

    fixed_opening = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Variables
    variables: dict = {}

    # Opening decisions
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        variables[f"y_{c}"] = var

    # Shipment decisions
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)
            variables[key] = var

    model.update()

    # Demand constraints: sum_c f_c_s >= demand_s
    for s in stores:
        model.addConstr(
            quicksum(variables[f"f_{c}_{s}"] for c in centers) >= demand[s],
            name=f"demand_{s}"
        )

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(
            quicksum(variables[f"f_{c}_{s}"] for s in stores) <= capacity[c] * variables[f"y_{c}"],
            name=f"cap_{c}"
        )

    # Objective: minimize opening costs + transportation costs
    opening_cost = quicksum(fixed_opening[c] * variables[f"y_{c}"] for c in centers)
    transport_cost_sum = quicksum(
        transport_cost[c][s] * variables[f"f_{c}_{s}"] for c in centers for s in stores
    )
    model.setObjective(opening_cost + transport_cost_sum, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    import gurobipy as gp
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    # Build solution vector
    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    objective_value = float(model.ObjVal)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }