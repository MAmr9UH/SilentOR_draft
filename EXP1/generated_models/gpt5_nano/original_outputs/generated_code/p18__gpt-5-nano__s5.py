import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    capacity = data["capacity"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]

    model = gp.Model("SupplyChain_Distribution")

    # Decision variables
    y = {}
    for c in centers:
        key = f"y_{c}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(f"f_i_j" * 0 for f_i_j in [])  # placeholder to keep syntax valid
    # Build objective directly
    obj_transport = gp.quicksum(transport_cost[c][s] * f[f"{c}_{s}"] for c in centers for s in stores)
    obj_opening = gp.quicksum(fixed_opening_cost[c] * y[f"y_{c}"] for c in centers)
    model.setObjective(obj_transport + obj_opening, GRB.MINIMIZE)

    # Constraints
    # Demand constraints: sum_c f_{c}_{s} == demand[s]
    for s in stores:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_{c}_{s} <= capacity[c] * y_{c}
    for c in centers:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for s in stores) <= capacity[c] * y[f"y_{c}"], name=f"cap_{c}")

    # Prepare return dictionary of variables
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[f"y_{c}"]
        for s in stores:
            variables[f"f_{c}_{s}"] = f[f"{c}_{s}"]

    return model, variables

def solve(data: dict) -> dict:
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

    objective_value = float(model.ObjVal)

    solution = {}
    centers = data["centers"]
    stores = data["stores"]
    for c in centers:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
        for s in stores:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    result = {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }

    return result