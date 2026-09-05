import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # y_c variables (opening decisions)
    y_vars = {}
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y_vars[c] = var
        variables[f"y_{c}"] = var

    # f_c_s variables (shipments)
    f_vars = {}
    for c in centers:
        for s in stores:
            var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}")
            f_vars[(c, s)] = var
            variables[f"f_{c}_{s}"] = var

    model.update()

    # Constraints
    # Demand satisfaction: sum_c f_c_s == demand_s
    for s in stores:
        model.addConstr(quicksum(f_vars[(c, s)] for c in centers) == data["demand"][s], name=f"Dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(quicksum(f_vars[(c, s)] for s in stores) <= data["capacity"][c] * y_vars[c], name=f"Cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = quicksum(data["fixed_opening_cost"][c] * y_vars[c] for c in centers)
    transport_cost = quicksum(data["transport_cost"][c][s] * f_vars[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    model.update()

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Build status string
    status_int = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_int, str(status_int))

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Solution vector
    solution = {}

    centers = data["centers"]
    stores = data["stores"]

    for c in centers:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    for c in centers:
        for s in stores:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }