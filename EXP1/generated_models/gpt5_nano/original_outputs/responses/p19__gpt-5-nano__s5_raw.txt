import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Variables
    y_vars = {}
    for c in centers:
        key = f"y_{c}"
        y_vars[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f_vars = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            f_vars[key] = model.addVar(vtype=GRB.CONTINUOUS, name=key, lb=0.0)

    model.update()

    # Demand constraints: sum_c f_{c,s} == demand_s
    for s in stores:
        demand = data["demand"][s]
        model.addConstr(
            quicksum(f_vars[f"{c}_{s}"] for c in centers) == demand,
            name=f"demand_{s}"
        )

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        capacity = data["capacity"][c]
        model.addConstr(
            quicksum(f_vars[f"{c}_{s}"] for s in stores) <= capacity * y_vars[f"y_{c}"],
            name=f"cap_{c}"
        )

    # Objective: minimize fixed opening costs + transportation costs
    opening_cost = quicksum(data["fixed_opening_cost"][c] * y_vars[f"y_{c}"] for c in centers)
    transport_cost = quicksum(
        data["transport_cost"][c][s] * f_vars[f"{c}_{s}"] for c in centers for s in stores
    )
    model.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    # Prepare variables dict with EXACT keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y_vars[f"y_{c}"]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f_vars[f"{c}_{s}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(status_code, str(status_code))
    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }