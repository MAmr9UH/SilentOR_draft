import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for i, c in enumerate(centers, start=1):
        key = f"y_c{i}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    fvars = {}
    for i, c in enumerate(centers, start=1):
        for j, s in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            fvars[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)

    # Objective: minimize opening costs + transportation costs
    opening_cost_expr = gp.quicksum(fixed_opening_cost[c] * y[f"y_c{i}"] for i, c in enumerate(centers, start=1))
    transport_cost_expr = gp.quicksum(
        transport_cost[c][s] * fvars[f"f_c{i}_s{j}"]
        for i, c in enumerate(centers, start=1)
        for j, s in enumerate(stores, start=1)
    )
    model.setObjective(opening_cost_expr + transport_cost_expr, GRB.MINIMIZE)

    # Demand constraints: meet demand at each store
    for j, s in enumerate(stores, start=1):
        model.addConstr(
            gp.quicksum(fvars[f"f_c{i}_s{j}"] for i in range(1, len(centers) + 1)) == demand[s],
            name=f"dem_{s}"
        )

    # Capacity constraints: total shipments from a center <= capacity * y_center
    for i, c in enumerate(centers, start=1):
        model.addConstr(
            gp.quicksum(fvars[f"f_c{i}_s{j}"] for j in range(1, len(stores) + 1)) <= capacity[c] * y[f"y_c{i}"],
            name=f"cap_{c}"
        )

    # Collect variables into the required output dictionary format
    variables = {}
    variables.update(y)
    variables.update(fvars)

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
    status = model.Status
    status_str = status_map.get(status, str(status))

    objective_value = float(model.ObjVal)

    # Build solution dictionary with exact keys
    solution = {}
    # y variables
    for i in range(1, 8):
        key = f"y_c{i}"
        solution[key] = float(variables[key].X)

    # flow variables
    for i in range(1, 8):
        for j in range(1, 5):
            key = f"f_c{i}_s{j}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }