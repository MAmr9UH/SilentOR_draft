from gurobipy import GRB, Model, quicksum

def build_model(data: dict) -> tuple:
    model = Model()
    batches = data["batches"]
    vats = data["vats"]
    positions = data["positions"]

    # Process times
    processing_time = data["processing_time"]
    p = {i: {v: float(processing_time[str(i)][str(v)]) for v in vats} for i in batches}

    # Decision variables
    y = {}
    for i in batches:
        for k in positions:
            y[(i, k)] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{k}")

    C = {}
    for k in positions:
        for v in vats:
            C[(k, v)] = model.addVar(vtype=GRB.CONTINUOUS, name=f"C_{k}_{v}", lb=0.0)

    Cmax = model.addVar(vtype=GRB.CONTINUOUS, name="Cmax", lb=0.0)

    model.update()

    # 1) Each batch assigned to exactly one position
    for i in batches:
        model.addConstr(quicksum(y[(i, k)] for k in positions) == 1, name=f"AssignBatch_{i}")

    # 2) Each position holds exactly one batch
    for k in positions:
        model.addConstr(quicksum(y[(i, k)] for i in batches) == 1, name=f"FillPosition_{k}")

    # 3) Sequence constraints on each vat
    for v in vats:
        for idx, k in enumerate(positions, start=1):
            p_sum = quicksum(p[i][v] * y[(i, k)] for i in batches)
            if k == positions[0]:
                model.addConstr(C[(k, v)] >= p_sum, name=f"Seq_{k}_{v}")
            else:
                model.addConstr(C[(k, v)] >= C[(k - 1, v)] + p_sum, name=f"Seq_{k}_{v}")

    # 4) Inter-machine linkage (same position across vats)
    M = 1e6
    for v in [2, 3]:
        for i in batches:
            for k in positions:
                model.addConstr(C[(k, v)] >= C[(k, v - 1)] + p[i][v] - M * (1 - y[(i, k)]),
                                name=f"Flow_i{i}_k{k}_v{v}")

    # 5) Cmax should be at least the makespan on last vat
    for k in positions:
        model.addConstr(Cmax >= C[(k, 3)], name=f"Cmax_ge_k{k}")

    model.setObjective(Cmax, GRB.MINIMIZE)

    # Return model and a dict of all variables with required keys
    variables = {}
    for i in batches:
        for k in positions:
            variables[f"y_{i}_{k}"] = y[(i, k)]
    for k in positions:
        for v in vats:
            variables[f"C_{k}_{v}"] = C[(k, v)]
    variables["Cmax"] = Cmax

    return model, variables


def solve(data: dict) -> dict:
    from gurobipy import GRB
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_val = float(model.ObjVal)

    # Build solution dictionary with exact keys
    solution = {}
    batches = data["batches"]
    positions = data["positions"]
    vats = data["vats"]

    for i in batches:
        for k in positions:
            solution[f"y_{i}_{k}"] = float(variables[f"y_{i}_{k}"].X)

    for k in positions:
        for v in vats:
            solution[f"C_{k}_{v}"] = float(variables[f"C_{k}_{v}"].X)

    solution["Cmax"] = float(variables["Cmax"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }