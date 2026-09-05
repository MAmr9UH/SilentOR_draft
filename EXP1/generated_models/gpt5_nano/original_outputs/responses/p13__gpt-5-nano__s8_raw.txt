import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening = data["fixed_opening_cost"]
    transport = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Variables container with exact keys required
    variables = {}

    # Opening decision variables y_c1 ... y_c4
    y = {}
    for idx, c in enumerate(centers, start=1):
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y[c] = var
        variables[f"y_c{idx}"] = var

    # Transportation variables f_cX_sY
    for c in centers:
        for s in stores:
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
            key = f"f_{c}_{s}"
            variables[key] = var

    model.update()

    # Demand constraints: sum_i f_{i,s} == demand_s
    for s in stores:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == demand[s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        cap = capacity[c]
        expr = gp.quicksum(variables[f"{c}_{s}"] for s in stores)
        model.addConstr(expr <= cap * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(fixed_opening[c] * y[c] for c in centers)
    transport_cost = gp.quicksum(transport[c][s] * variables[f"{c}_{s}"] for c in centers for s in stores)
    model.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_code, str(status_code))
    objective = float(model.ObjVal)

    # Build solution dictionary with exact keys
    solution = {}
    for key in ["y_c1", "y_c2", "y_c3", "y_c4"]:
        solution[key] = float(variables[key].X)

    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }