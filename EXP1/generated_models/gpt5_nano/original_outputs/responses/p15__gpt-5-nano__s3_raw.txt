import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()
    centers = data["centers"]
    stores = data["stores"]

    # Decision variables
    variables = {}

    # y_c1 ... y_c5
    for idx, c in enumerate(centers, start=1):
        key = f"y_c{idx}"
        v = model.addVar(vtype=gp.GRB.BINARY, name=key)
        variables[key] = v

    # f_cX_sY
    for i, c in enumerate(centers, start=1):
        for j, s in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            v = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum over centers f_ci_sj = demand_j
    for j, s in enumerate(stores, start=1):
        expr = gp.quicksum(variables[f"f_c{i}_s{j}"] for i in range(1, len(centers) + 1))
        model.addConstr(expr == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_ci_s <= capacity_ci * y_ci
    for i, c in enumerate(centers, start=1):
        cap = data["capacity"][f"c{i}"]
        expr = gp.quicksum(variables[f"f_c{i}_s{j}"] for j in range(1, len(stores) + 1))
        model.addConstr(expr <= cap * variables[f"y_c{i}"], name=f"cap_c{i}")

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][f"c{i}"] * variables[f"y_c{i}"] for i in range(1, len(centers) + 1))
    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            obj += data["transport_cost"][f"c{i}"][f"s{j}"] * variables[f"f_c{i}_s{j}"]

    model.setObjective(obj, sense=gp.GRB.MINIMIZE)

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    model.update()

    # Build solution dictionary with all variable values
    solution = {}
    for i in range(1, len(data["centers"]) + 1):
        solution[f"y_c{i}"] = float(variables[f"y_c{i}"].X)
    for i in range(1, len(data["centers"]) + 1):
        for j in range(1, len(data["stores"]) + 1):
            solution[f"f_c{i}_s{j}"] = float(variables[f"f_c{i}_s{j}"].X)

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }
    return result