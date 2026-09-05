def build_model(data: dict):
    from gurobipy import Model, GRB, quicksum

    model = Model()
    model.setParam('OutputFlag', 0)

    container_ids = data["container_ids"]
    goods = data["goods"]
    weights = data["weight_tons"]
    quantities = data["quantity"]

    # Decision variables
    y = {}
    uA = {}
    q = {}

    variables = {}

    # Upper bound for A to set big-M
    M_A = quantities["A"]

    for i in container_ids:
        y_i = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")
        y[i] = y_i
        variables[f"y_{i}"] = y_i

        uA_i = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")
        uA[i] = uA_i
        variables[f"uA_{i}"] = uA_i

        for G in goods:
            v = model.addVar(vtype=GRB.INTEGER, name=f"q_{i}_{G}")
            q[(i, G)] = v
            variables[f"q_{i}_{G}"] = v

    model.update()

    # Quantity balance for each good
    for G in goods:
        model.addConstr(quicksum(q[(i, G)] for i in container_ids) == quantities[G])

    # Per-container capacity and minimum loading
    capacity = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    min_D = data["minimum_D_units_if_used"]

    for i in container_ids:
        total_weight = quicksum(weights[G] * q[(i, G)] for G in goods)

        model.addConstr(total_weight <= capacity * y[i])
        model.addConstr(total_weight >= min_load * y[i])

        # Minimum D units if container is used
        model.addConstr(q[(i, "D")] >= min_D * y[i])

        # A-C association: A ≤ M_A * uA_i and A ≥ uA_i
        model.addConstr(q[(i, "A")] <= M_A * uA[i])
        model.addConstr(q[(i, "A")] >= uA[i])

        # If any A is loaded in container, at least one C must be loaded
        model.addConstr(q[(i, "C")] >= uA[i])

    objective = sum(y[i] for i in container_ids)
    model.setObjective(objective, GRB.MINIMIZE)

    return model, variables

def solve(data: dict):
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    solution = {}
    for i in range(1, 11):
        solution[f"y_{i}"] = int(variables[f"y_{i}"].X)
    for i in range(1, 11):
        solution[f"uA_{i}"] = int(variables[f"uA_{i}"].X)
    goods = data["goods"]
    for i in range(1, 11):
        for G in goods:
            solution[f"q_{i}_{G}"] = int(variables[f"q_{i}_{G}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }