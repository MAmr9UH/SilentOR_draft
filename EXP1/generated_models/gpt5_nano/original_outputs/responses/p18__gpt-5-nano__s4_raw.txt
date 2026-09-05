import sys
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = Model()
    # Silence solver output if possible
    try:
        model.Params.LogToConsole = 0
    except Exception:
        pass
    # Decision variables
    y_vars = {}
    for ci in centers:
        key = f"y_{ci}"
        y_vars[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f_vars = {}
    for ci in centers:
        for si in stores:
            key = f"f_{ci}_{si}"
            f_vars[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    obj = quicksum(opening_cost[ci] * y_vars[f"y_{ci}"] for ci in centers) \
        + quicksum(transport_cost[ci][si] * f_vars[f"{'f_'+ci+'_'+si}"] for ci in centers for si in stores)
    model.setObjective(obj, GRB.MINIMIZE)

    # Demand constraints: meet each store's demand
    for si in stores:
        demand_s = data["demand"][si]
        model.addConstr(quicksum(f_vars[f"f_{ci}_{si}"] for ci in centers) == demand_s, name=f"demand_{si}")

    # Capacity constraints: sum shipments from a center <= capacity * open
    for ci in centers:
        cap = data["capacity"][ci]
        model.addConstr(quicksum(f_vars[f"f_{ci}_{si}"] for si in stores) <= cap * y_vars[f"y_{ci}"], name=f"cap_{ci}")

    # Build the variables dictionary to return
    variables = {}
    for ci in centers:
        variables[f"y_{ci}"] = y_vars[f"y_{ci}"]
    for ci in centers:
        for si in stores:
            variables[f"f_{ci}_{si}"] = f_vars[f"f_{ci}_{si}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status, str(status))

    objective = float(model.ObjVal) if model.ObjVal is not None else float('nan')

    # Collect solution values
    solution_vals = {}
    for key, var in variables.items():
        try:
            solution_vals[key] = var.X
        except Exception:
            # In case of detached variables, skip
            solution_vals[key] = None

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution_vals
    }