import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()

    months = data["months"]
    demand_by_month = {int(m): int(data["demand_100sqm"][str(m)]) for m in months}
    feasible_pairs = [tuple(p) for p in data["feasible_start_length_pairs"]]
    fees_by_length = {int(k): int(v) for k, v in data["fee_per_100sqm_by_length"].items()}
    min_distinct = int(data["min_distinct_lengths"])
    max_distinct = int(data["max_distinct_lengths"])
    mut_exclusive = data.get("mutually_exclusive_lengths", [])

    # Big M for linking x and y (set reasonably large)
    BigM = 1000

    # Decision variables
    x_vars = {}
    feasible_set = set(feasible_pairs)
    for (s, l) in feasible_pairs:
        key = f"x_{s}_{l}"
        x_vars[key] = model.addVar(vtype=gp.GRB.INT, lb=0, name=key)

    y_vars = {}
    for l in data["contract_lengths"]:
        key = f"y_{l}"
        y_vars[key] = model.addVar(vtype=gp.GRB.BINARY, lb=0, name=key)

    model.update()

    # Objective: minimize total rental cost
    obj = gp.quicksum(x_vars[f"x_{s}_{l}"] * fees_by_length[int(l)] for (s, l) in feasible_pairs)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Demand satisfaction constraints (monthly)
    for m in months:
        terms = []
        for (s, l) in feasible_pairs:
            if s <= m <= s + l - 1:
                terms.append(x_vars[f"x_{s}_{l}"])
        model.addConstr(gp.quicksum(terms) == demand_by_month[m])

    # Distinct lengths constraints
    sum_y = gp.quicksum(y_vars[f"y_{l}"] for l in data["contract_lengths"])
    model.addConstr(sum_y >= min_distinct)
    model.addConstr(sum_y <= max_distinct)

    # Mutually exclusive lengths
    # Interpret mut_exclusive as a set of lengths that are mutually exclusive pairwise
    for i in range(len(mut_exclusive)):
        for j in range(i + 1, len(mut_exclusive)):
            a = int(mut_exclusive[i])
            b = int(mut_exclusive[j])
            model.addConstr(y_vars[f"y_{a}"] + y_vars[f"y_{b}"] <= 1)

    # If a 4-month contract is chosen, then no 1-month contract may be chosen
    for s in range(1, 5):
        if (s, 1) in feasible_set:
            model.addConstr(x_vars[f"x_{s}_1"] <= BigM * (1 - y_vars["y_4"]))

    model.update()

    # Return model and all variables in a flat dict with exact keys
    variables = {}
    for k, v in x_vars.items():
        variables[k] = v
    for k, v in y_vars.items():
        variables[k] = v

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.Params.LogToConsole = 0
    model.optimize()

    # Status mapping
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Extract solution values
    solution_keys = [
        "x_1_1", "x_1_2", "x_1_3", "x_1_4",
        "x_2_1", "x_2_2", "x_2_3",
        "x_3_1", "x_3_2",
        "x_4_1",
        "y_1", "y_2", "y_3", "y_4"
    ]

    solution = {}
    for key in solution_keys:
        v = variables[key].X
        solution[key] = int(round(v))

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }