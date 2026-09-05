from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    """
    Build and return a Gurobi MILP model for the warehouse renting problem.
    The function does not call optimize().
    It returns:
      - model: the gurobipy Model
      - variables: a dict with the exact structure required:
          {
            "variables_keys": { "x_1_1": Var, "x_1_2": Var, ..., "y_4": Var },
            "note": "Use flat variables x_StartMonth_Length for contract counts and y_Length for length-use binaries. Demand is measured in 100-square-meter units."
          }
    """
    # Initialize model
    model = Model()

    # Data extraction
    months = data["months"]  # list of months (ints)
    feasible_pairs = data["feasible_start_length_pairs"]  # list of [start, length]
    demand_per_month = data["demand_100sqm"]  # dict with keys as strings "1","2",...
    contract_lengths = data["contract_lengths"]  # list of lengths
    fee_by_length = data["fee_per_100sqm_by_length"]  # dict with keys as strings
    min_distinct = data["min_distinct_lengths"]
    max_distinct = data["max_distinct_lengths"]
    mutually_exclusive = data.get("mutually_exclusive_lengths", [])  # list of pairs e.g., [1,4]

    # Decision variables
    # x_{s}_{l}: integer number of 100sqm contracts starting in month s with length l
    x = {}
    for (s, l) in feasible_pairs:
        var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x[(s, l)] = var

    # y_l: binary variable indicating whether any contract of length l is used
    y = {}
    for l in contract_lengths:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{l}")
        y[l] = var

    model.update()

    # Demand constraints: for each month t, sum of active contracts covering t >= demand[t]
    for t in months:
        demand = int(demand_per_month[str(t)])
        active = quicksum(x[(s, l)] for (s, l) in feasible_pairs if s <= t <= s + l - 1)
        model.addConstr(active >= demand, name=f"demand_{t}")

    # Link constraints: sum of x for a given length l must be >= y_l
    for L in contract_lengths:
        sum_with_length = quicksum(x[(s, l)] for (s, l) in feasible_pairs if l == L)
        model.addConstr(sum_with_length >= y[L], name=f"cover_length_{L}")

    # Distinct length constraints
    model.addConstr(quicksum(y[L] for L in contract_lengths) >= min_distinct, name="min_distinct_lengths")
    model.addConstr(quicksum(y[L] for L in contract_lengths) <= max_distinct, name="max_distinct_lengths")

    # 4-month contract cannot coexist with 1-month contract
    if 4 in contract_lengths and 1 in contract_lengths:
        model.addConstr(y[4] + y[1] <= 1, name="no_1_and_4")

    # Mutually exclusive length pairs
    for (a, b) in mutually_exclusive:
        model.addConstr(y[a] + y[b] <= 1, name=f"mutual_exclusive_{a}_{b}")

    # Objective: minimize total cost
    total_cost = quicksum(x[(s, l)] * int(fee_by_length[str(l)]) for (s, l) in feasible_pairs)
    model.setObjective(total_cost, GRB.MINIMIZE)

    # Prepare variables dictionary to return
    var_map = {}
    # x variables
    for (s, l) in feasible_pairs:
        var_map[f"x_{s}_{l}"] = x[(s, l)]
    # y variables
    for L in contract_lengths:
        var_map[f"y_{L}"] = y[L]

    variables = {
        "variables_keys": var_map,
        "note": "Use flat variables x_StartMonth_Length for contract counts and y_Length for length-use binaries. Demand is measured in 100-square-meter units."
    }

    return model, variables


def solve(data: dict) -> dict:
    """
    Solve the MILP instance defined by data.
    Returns a dict with status, objective value, and solution for all required variables.
    """
    model, variables = build_model(data)
    model.optimize()

    # Decode status
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(st)

    # Objective value
    if st in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INFEASIBLE, GRB.UNBOUNDED, GRB.INF_OR_UNBD):
        try:
            obj_val = float(model.ObjVal)
        except Exception:
            obj_val = 0.0
    else:
        obj_val = 0.0

    # Build solution dictionary
    sol = {}
    # Expected keys for x variables
    x_keys = ["x_1_1", "x_1_2", "x_1_3", "x_1_4", "x_2_1", "x_2_2", "x_2_3", "x_3_1", "x_3_2", "x_4_1"]
    # y variables
    y_keys = ["y_1", "y_2", "y_3", "y_4"]

    # Fetch values (default to 0 if not solved)
    var_map = variables.get("variables_keys", {})
    for k in x_keys:
        v = var_map.get(k)
        sol[k] = float(v.X) if v is not None else 0.0
    for k in y_keys:
        v = var_map.get(k)
        sol[k] = float(v.X) if v is not None else 0.0

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": sol
    }