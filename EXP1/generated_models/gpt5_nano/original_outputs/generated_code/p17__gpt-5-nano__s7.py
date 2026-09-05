import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("LogistiCorp")

    centers = data["centers"]
    stores = data["stores"]

    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y_vars = {}
    for c in centers:
        y_vars[f"y_{c}"] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f_vars = {}
    for c in centers:
        for s in stores:
            f_vars[f"f_{c}_{s}"] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Demand constraints: meet exact demand at each store
    for s in stores:
        expr = gp.quicksum(f_vars[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == demand[s], name=f"dem_{s}")

    # Capacity constraints: each center's shipments do not exceed capacity if opened
    for c in centers:
        expr = gp.quicksum(f_vars[f"f_{c}_{s}"] for s in stores)
        model.addConstr(expr <= capacity[c] * y_vars[f"y_{c}"], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(fixed_opening_cost[c] * y_vars[f"y_{c}"] for c in centers)
    transport_cost_sum = gp.quicksum(
        transport_cost[c][s] * f_vars[f"f_{c}_{s}"] for c in centers for s in stores
    )
    model.setObjective(opening_cost + transport_cost_sum, GRB.MINIMIZE)

    # Prepare the return variable dictionary with exactly the required keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y_vars[f"y_{c}"]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f_vars[f"f_{c}_{s}"]

    return model, variables

def solve(data: dict) -> dict:
    import gurobipy as gp

    model, variables = build_model(data)
    model.optimize()

    # Map status to string
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

    objective_value = float(model.ObjVal)

    # Build solution dictionary in the required order
    solution = {}
    keys_order = []
    for c in data["centers"]:
        keys_order.append(f"y_{c}")
    for c in data["centers"]:
        for s in data["stores"]:
            keys_order.append(f"f_{c}_{s}")

    for k in keys_order:
        solution[k] = float(variables[k].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }