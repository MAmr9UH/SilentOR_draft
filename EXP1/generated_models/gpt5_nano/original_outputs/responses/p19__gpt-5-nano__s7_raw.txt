import gurobipy as gp

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # Opening variables
    for c in centers:
        key = f"y_{c}"
        variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    # Transportation variables
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers)
    for c in centers:
        for s in stores:
            obj += data["transport_cost"][c][s] * variables[f"f_{c}_{s}"]
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Demands constraints: meet exactly the demand for each store
    for s in stores:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for c in centers)
        model.addConstr(expr == data["demand"][s], name=f"demand_{s}")

    # Capacities constraints: can't ship more than capacity if not opened
    for c in centers:
        expr = gp.quicksum(variables[f"{'f_'+c}_{s}"] for s in stores)
        model.addConstr(expr <= data["capacity"][c] * variables[f"y_{c}"], name=f"cap_{c}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    objective = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }