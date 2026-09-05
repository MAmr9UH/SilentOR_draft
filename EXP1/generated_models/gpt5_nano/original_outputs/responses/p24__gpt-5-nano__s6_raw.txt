from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    container_ids = data.get("container_ids", [])
    goods = data.get("goods", [])
    n = len(container_ids)
    quantities = data.get("quantity", {})
    weights = data.get("weight_tons", {})
    max_capacity = data.get("container_capacity_tons", 60)
    min_load = data.get("minimum_load_tons_if_used", 18)
    A_total = quantities.get("A", 0)

    model = Model()
    model.Params.LogToConsole = 0  # quiet

    # Decision variables
    variables = {}

    y = {}
    uA = {}
    q = {}

    for i in range(1, n + 1):
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")
        variables[f"y_{i}"] = y[i]

        uA[i] = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")
        variables[f"uA_{i}"] = uA[i]

        for g in goods:
            var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"q_{i}_{g}")
            q[(i, g)] = var
            variables[f"q_{i}_{g}"] = var

    model.update()

    # Capacity and minimum load per container, and A->C constraint
    for i in range(1, n + 1):
        total_weight_i = quicksum(weights[g] * q[(i, g)] for g in goods)
        model.addConstr(total_weight_i <= max_capacity * y[i])
        model.addConstr(total_weight_i >= min_load * y[i])

        # A presence and C presence constraint
        sum_A_i = q[(i, "A")]
        sum_C_i = q[(i, "C")]
        model.addConstr(sum_A_i <= A_total * uA[i])
        model.addConstr(sum_A_i >= uA[i])
        model.addConstr(sum_C_i >= uA[i])

    # Totals for each good
    for g in goods:
        model.addConstr(quicksum(q[(i, g)] for i in range(1, n + 1)) == quantities[g])

    # Objective: minimize number of containers used
    model.setObjective(quicksum(y[i] for i in range(1, n + 1)), GRB.MINIMIZE)

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(int(model.Status)))

    objective = int(model.ObjVal) if model.ObjVal is not None else None

    container_ids = data.get("container_ids", [])
    goods = data.get("goods", [])
    n = len(container_ids)

    solution = {}

    # y variables
    for i in range(1, n + 1):
        solution[f"y_{i}"] = int(variables[f"y_{i}"].X)

    # uA variables
    for i in range(1, n + 1):
        solution[f"uA_{i}"] = int(variables[f"uA_{i}"].X)

    # q variables in order q_1_A, q_1_B, ..., q_10_E
    for i in range(1, n + 1):
        for g in goods:
            solution[f"q_{i}_{g}"] = int(variables[f"q_{i}_{g}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }