import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model("warehouse_rental_milp")

    months = data.get("months", [])
    demand = data["demand_100sqm"]
    # Build demand for each month as int
    demand_m = {m: int(demand[str(m)]) for m in months}

    feasible_pairs = [tuple(pair) for pair in data["feasible_start_length_pairs"]]
    lengths = sorted({l for (_s, l) in feasible_pairs for _ in [0] for _ in [0] if True})  # unique lengths present
    # Correct extraction of unique lengths from feasible pairs
    lengths = sorted({l for (_s, l) in feasible_pairs})

    min_distinct = data["min_distinct_lengths"]
    max_distinct = data["max_distinct_lengths"]
    mutually_exclusive = data.get("mutually_exclusive_lengths", [])

    # Create decision variables
    x_vars = {}
    for (s, l) in feasible_pairs:
        var = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x_vars[(s, l)] = var

    y_vars = {}
    for l in lengths:
        var = model.addVar(vtype=gp.GRB.BINARY, lb=0, ub=1, name=f"y_{l}")
        y_vars[l] = var

    model.update()

    # Demand constraints: for each month m, sum of active contracts covering m equals demand
    for m in months:
        demand_value = int(demand[str(m)])
        expr = gp.quicksum(x_vars[(s, l)]
                           for (s, l) in feasible_pairs
                           if (s <= m <= s + l - 1))
        model.addConstr(expr == demand_value)

    # Capacity constraints linking x and y (per length)
    bigM = sum(demand_m.values())  # a safe upper bound on the total number of contracts of a given length
    for l in lengths:
        expr_len = gp.quicksum(x_vars[(s, l2)]
                               for (s, l2) in feasible_pairs
                               if l2 == l)
        model.addConstr(expr_len <= bigM * y_vars[l])
        model.addConstr(expr_len >= y_vars[l])

    # Distinct lengths constraints
    sum_y = gp.quicksum(y_vars[l] for l in lengths)
    model.addConstr(sum_y <= max_distinct)
    model.addConstr(sum_y >= min_distinct)

    # Mutually exclusive lengths
    for i in range(len(mutually_exclusive)):
        a = mutually_exclusive[i]
        for j in range(i + 1, len(mutually_exclusive)):
            b = mutually_exclusive[j]
            if a in y_vars and b in y_vars:
                model.addConstr(y_vars[a] + y_vars[b] <= 1)

    # Objective: minimize total rental cost
    obj = gp.quicksum(data["fee_per_100sqm_by_length"][str(l)] * x_vars[(s, l)]
                      for (s, l) in feasible_pairs)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Prepare the variables dictionary with exact keys required
    variables = {}
    for (s, l), var in x_vars.items():
        variables[f"x_{s}_{l}"] = var
    for l, var in y_vars.items():
        variables[f"y_{l}"] = var

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    obj_val = model.ObjVal

    # Build solution dict with the required keys
    keys = ["x_1_1","x_1_2","x_1_3","x_1_4","x_2_1","x_2_2","x_2_3","x_3_1","x_3_2","x_4_1","y_1","y_2","y_3","y_4"]
    solution = {}
    for k in keys:
        v = variables.get(k)
        if v is None:
            solution[k] = None
        else:
            val = v.X
            if isinstance(val, float) and abs(val - round(val)) < 1e-6:
                val = int(round(val))
            solution[k] = val

    return {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": solution
    }