import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("LogiChain")

    # Decision variables
    y_vars = {}
    for c in centers:
        y = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y_vars[c] = y

    f_vars = {}
    for c in centers:
        for s in stores:
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")
            f_vars[(c, s)] = v

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][c] * y_vars[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += data["transport_cost"][c][s] * f_vars[(c, s)]
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints: meet demand at each store
    for s in stores:
        model.addConstr(gp.quicksum(f_vars[(c, s)] for c in centers) == data["demand"][s], name=f"Dem_{s}")

    # Constraints: capacity of each center (only if opened)
    for c in centers:
        model.addConstr(gp.quicksum(f_vars[(c, s)] for s in stores) <= data["capacity"][c] * y_vars[c], name=f"Cap_{c}")

    # Collect variables into a flat dictionary with exact keys requested
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y_vars[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f_vars[(c, s)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    else:
        status_str = "UNKNOWN"

    objective = model.ObjVal

    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }