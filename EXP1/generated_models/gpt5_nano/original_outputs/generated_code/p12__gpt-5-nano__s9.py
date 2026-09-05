import gurobipy as gp

def _status_to_string(st: int) -> str:
    if st == gp.GRB.OPTIMAL:
        return "OPTIMAL"
    if st == gp.GRB.INFEASIBLE:
        return "INFEASIBLE"
    if st == gp.GRB.UNBOUNDED:
        return "UNBOUNDED"
    if st == gp.GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if st == gp.GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    if st == gp.GRB.SOLUTION_LIMIT:
        return "SOLUTION_LIMIT"
    if st == gp.GRB.NODELIMIT:
        return "NODELIMIT"
    if st == gp.GRB.INTERRUPTED:
        return "INTERRUPTED"
    return str(st)

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for c in centers:
        y[c] = model.AddVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.AddVar(vtype=gp.GRB.CONTINUOUS, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = gp.quicksum(f[c][s] * transport_cost[c][s] for c in centers for s in stores)  \
                        + gp.quicksum(y[c] * fixed_opening_cost[c] for c in centers)
    model.setObjective(opening_cost_term, gp.GRB.MINIMIZE)

    # Demand constraints: meet exact demand at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: shipments from a center cannot exceed its capacity if opened
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Prepare the variables dictionary with exact keys expected by the interface
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_str = _status_to_string(status_int)
    obj_val = float(model.ObjVal)

    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }