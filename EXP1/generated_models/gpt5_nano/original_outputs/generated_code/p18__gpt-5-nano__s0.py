import sys
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = Model()
    # Optional: silence solver output
    try:
        model.setParam("OutputFlag", 0)
    except Exception:
        pass

    variables = {}

    # Open decision variables
    y_vars = {}
    for c in centers:
        key = f"y_{c}"
        var = model.addVar(vtype=GRB.BINARY, name=key)
        y_vars[c] = var
        variables[key] = var

    # Shipment variables f_c_s
    f_vars = {}
    for c in centers:
        row = {}
        for s in stores:
            key = f"f_{c}_{s}"
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            row[s] = var
            variables[key] = var
        f_vars[c] = row

    model.update()

    # Demand constraints: sum_c f_c_s >= demand_s
    for s in stores:
        model.addConstr(quicksum(f_vars[c][s] for c in centers) >= demand[s], name=f"Dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        model.addConstr(quicksum(f_vars[c][s] for s in stores) <= capacity[c] * y_vars[c], name=f"Cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = quicksum(fixed_opening_cost[c] * y_vars[c] for c in centers)
    transport_cost_term = quicksum(transport_cost[c][s] * f_vars[c][s] for c in centers for s in stores)
    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }