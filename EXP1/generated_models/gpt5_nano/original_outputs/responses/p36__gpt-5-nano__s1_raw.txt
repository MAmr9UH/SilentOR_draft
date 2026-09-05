import gurobipy as gp

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Prepare data
    months = data["months"]  # list of months
    demand_by_month = {m: data["demand_100sqm"][str(m)] for m in months}  # in 100sqm units
    feasible = data["feasible_start_length_pairs"]  # list of [start, length]
    contract_lengths = data["contract_lengths"]  # list of lengths
    fee_by_length = data["fee_per_100sqm_by_length"]  # dict with string keys
    min_distinct = data["min_distinct_lengths"]
    max_distinct = data["max_distinct_lengths"]

    # Determine M for big-M constraints
    M = max(demand_by_month.values()) if demand_by_month else 0
    if M <= 0:
        M = 1

    # Create decision variables
    x_vars = {}  # (start, length) -> Var
    for (s, l) in feasible:
        v = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x_vars[(s, l)] = v

    y_vars = {}  # length -> Var
    for l in contract_lengths:
        v = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{l}")
        y_vars[l] = v

    model.update()

    # Collect variables into the required dict format
    variables = {}
    for (s, l), v in x_vars.items():
        variables[f"x_{s}_{l}"] = v
    for l, v in y_vars.items():
        variables[f"y_{l}"] = v

    # Objective: minimize total rental cost
    model.setObjective(gp.quicksum(x_vars[(s, l)] * int(fee_by_length[str(l)]) for (s, l) in feasible), gp.GRB.MINIMIZE)

    # Demand constraints: for each month m, sum of covering contracts must equal demand
    for m in months:
        expr = gp.quicksum(x_vars[(s, l)]
                           for (s, l) in feasible if (s <= m <= s + l - 1))
        model.addConstr(expr == demand_by_month[m], name=f"demand_m{m}")

    # Link x and y: if a length l is used, then there must be at least one contract of that length
    for (s, l) in feasible:
        model.addConstr(x_vars[(s, l)] <= M * y_vars[l], name=f"link_x_y_{s}_{l}")

    for l in contract_lengths:
        # Ensure that if a length is used, the sum of its x vars is at least 1
        sum_x_for_l = gp.quicksum(x_vars[(s, l)] for (s, l2) in feasible if l2 == l)
        model.addConstr(sum_x_for_l >= y_vars[l], name=f"length_used_if_needed_{l}")

    # Distinct lengths constraint
    model.addConstr(gp.quicksum(y_vars[l] for l in contract_lengths) >= min_distinct, name="min_distinct_lengths")
    model.addConstr(gp.quicksum(y_vars[l] for l in contract_lengths) <= max_distinct, name="max_distinct_lengths")

    # Mutual exclusivity: if a 4-month contract is chosen, no 1-month contract may be chosen
    if 4 in contract_lengths:
        sum_x1 = gp.quicksum(x_vars[(s, 1)] for (s, l) in feasible if l == 1)
        model.addConstr(sum_x1 <= M * (1 - y_vars[4]), name="no_1_when_4")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Build solution dict with required keys
    solution = {
        "x_1_1": variables["x_1_1"].X if "x_1_1" in variables else None,
        "x_1_2": variables["x_1_2"].X if "x_1_2" in variables else None,
        "x_1_3": variables["x_1_3"].X if "x_1_3" in variables else None,
        "x_1_4": variables["x_1_4"].X if "x_1_4" in variables else None,
        "x_2_1": variables["x_2_1"].X if "x_2_1" in variables else None,
        "x_2_2": variables["x_2_2"].X if "x_2_2" in variables else None,
        "x_2_3": variables["x_2_3"].X if "x_2_3" in variables else None,
        "x_3_1": variables["x_3_1"].X if "x_3_1" in variables else None,
        "x_3_2": variables["x_3_2"].X if "x_3_2" in variables else None,
        "x_4_1": variables["x_4_1"].X if "x_4_1" in variables else None,
        "y_1": variables["y_1"].X if "y_1" in variables else None,
        "y_2": variables["y_2"].X if "y_2" in variables else None,
        "y_3": variables["y_3"].X if "y_3" in variables else None,
        "y_4": variables["y_4"].X if "y_4" in variables else None
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution
    }