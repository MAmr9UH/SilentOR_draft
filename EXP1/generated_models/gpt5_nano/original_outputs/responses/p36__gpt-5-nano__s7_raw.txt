import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi MILP model for the warehouse rental problem.

    Returns:
        model: The constructed gurobipy Model object (not optimized).
        variables: A dictionary with exact keys specified, mapped to gurobipy Var objects.
    """
    model = gp.Model()

    # Data extraction
    feasible = data["feasible_start_length_pairs"]  # list of [start, length]
    months = data["months"]  # e.g., [1,2,3,4]
    demand = {int(k): int(v) for k, v in data["demand_100sqm"].items()}  # in 100-sqm units
    contract_lengths = data["contract_lengths"]  # list of lengths
    fees = {int(k): int(v) for k, v in data["fee_per_100sqm_by_length"].items()}  # per 100 sqm
    min_dist = data["min_distinct_lengths"]
    max_dist = data["max_distinct_lengths"]

    # Decision variables
    x = {}  # x_s_l: number of 100-sqm contracts starting at month s with length l
    for (s, l) in feasible:
        var = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x[(s, l)] = var

    y = {}  # y_l: binary indicator if any contract of length l is used
    for l in contract_lengths:
        var = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{l}")
        y[l] = var

    model.update()

    # Demand satisfaction constraints: for each month t, sum of active contracts equals demand
    for t in months:
        active = gp.quicksum(x[(s, l)] for (s, l) in feasible if s <= t <= s + l - 1)
        model.addConstr(active == demand.get(t, 0), name=f"demand_{t}")

    # Linking constraints: sum_x_l <= BIG * y_l and sum_x_l >= y_l to encode y_l as an indicator
    BIG = 1e6
    for l in contract_lengths:
        sum_x_l = gp.quicksum(x[(s, ll)] for (s, ll) in feasible if ll == l)
        model.addConstr(sum_x_l <= BIG * y[l])
        model.addConstr(sum_x_l >= y[l])

    # Distinct lengths constraints
    model.addConstr(gp.quicksum(y[l] for l in contract_lengths) >= min_dist)
    model.addConstr(gp.quicksum(y[l] for l in contract_lengths) <= max_dist)

    # Rule: if a 4-month contract is chosen, then no 1-month contract may be chosen
    if 4 in contract_lengths:
        for (s, l) in feasible:
            if l == 1:
                model.addConstr(x[(s, 1)] <= BIG * (1 - y[4]))

    # Mutually exclusive lengths 1 and 4 (additional linear encoding)
    if (1 in contract_lengths) and (4 in contract_lengths):
        sum1 = gp.quicksum(x[(s, 1)] for (s, ll) in feasible if ll == 1)
        sum4 = gp.quicksum(x[(s, 4)] for (s, ll) in feasible if ll == 4)
        model.addConstr(sum1 <= BIG * (1 - y[4]))
        model.addConstr(sum4 <= BIG * (1 - y[1]))

    # Objective: minimize total rental cost
    objective = gp.quicksum(x[(s, l)] * fees[l] for (s, l) in feasible)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    # Prepare the variables dictionary to return
    variables = {
        "x_1_1": x.get((1, 1)),
        "x_1_2": x.get((1, 2)),
        "x_1_3": x.get((1, 3)),
        "x_1_4": x.get((1, 4)),
        "x_2_1": x.get((2, 1)),
        "x_2_2": x.get((2, 2)),
        "x_2_3": x.get((2, 3)),
        "x_3_1": x.get((3, 1)),
        "x_3_2": x.get((3, 2)),
        "x_4_1": x.get((4, 1)),
        "y_1": y[1] if 1 in y else None,
        "y_2": y[2] if 2 in y else None,
        "y_3": y[3] if 3 in y else None,
        "y_4": y[4] if 4 in y else None
    }

    return model, variables


def solve(data: dict) -> dict:
    """
    Solve the MILP problem by:
    - building the model,
    - optimizing it,
    - returning the required solution schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
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

    objective_value = float(model.ObjVal)

    # Build solution dictionary with required keys
    sol = {
        "x_1_1": int(variables["x_1_1"].X) if variables["x_1_1"] is not None else 0,
        "x_1_2": int(variables["x_1_2"].X) if variables["x_1_2"] is not None else 0,
        "x_1_3": int(variables["x_1_3"].X) if variables["x_1_3"] is not None else 0,
        "x_1_4": int(variables["x_1_4"].X) if variables["x_1_4"] is not None else 0,
        "x_2_1": int(variables["x_2_1"].X) if variables["x_2_1"] is not None else 0,
        "x_2_2": int(variables["x_2_2"].X) if variables["x_2_2"] is not None else 0,
        "x_2_3": int(variables["x_2_3"].X) if variables["x_2_3"] is not None else 0,
        "x_3_1": int(variables["x_3_1"].X) if variables["x_3_1"] is not None else 0,
        "x_3_2": int(variables["x_3_2"].X) if variables["x_3_2"] is not None else 0,
        "x_4_1": int(variables["x_4_1"].X) if variables["x_4_1"] is not None else 0,
        "y_1": int(variables["y_1"].X) if variables["y_1"] is not None else 0,
        "y_2": int(variables["y_2"].X) if variables["y_2"] is not None else 0,
        "y_3": int(variables["y_3"].X) if variables["y_3"] is not None else 0,
        "y_4": int(variables["y_4"].X) if variables["y_4"] is not None else 0,
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": sol
    }