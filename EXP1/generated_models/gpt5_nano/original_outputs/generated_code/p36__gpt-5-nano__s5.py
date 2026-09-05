import gurobipy as gp

def build_model(data: dict) -> tuple:
    # Parse data
    months = [int(m) for m in data.get("months", [])]
    demand_raw = data.get("demand_100sqm", {})
    demand = {int(k): int(v) for k, v in demand_raw.items()}
    feasible_pairs = [tuple(pair) for pair in data.get("feasible_start_length_pairs", [])]
    contract_lengths = [int(l) for l in data.get("contract_lengths", [])]
    fee_by_length_raw = data.get("fee_per_100sqm_by_length", {})
    fee_by_length = {int(k): int(v) for k, v in fee_by_length_raw.items()}
    min_distinct = int(data.get("min_distinct_lengths", 0))
    max_distinct = int(data.get("max_distinct_lengths", 0))
    mutually_exclusive = [int(l) for l in data.get("mutually_exclusive_lengths", [])]

    # Big-M
    M = sum(demand.values()) if demand else 0

    model = gp.Model()

    # Decision variables
    # x_{s}_{l}: integer number of 100-sqm contracts starting at month s with length l
    x = {}
    for s, l in feasible_pairs:
        x[(s, l)] = model.addVar(vtype=gp.GRB.INTEGER, name=f"x_{s}_{l}", lb=0)

    # y_{l}: binary indicator whether any contract of length l is used
    y = {}
    for l in contract_lengths:
        y[l] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{l}")

    model.update()

    # Demand satisfaction constraints: for each month m, sum of active contracts equals demand
    for m in months:
        model.addConstr(
            gp.quicksum(x[(s, l)] for (s, l) in feasible_pairs if s <= m <= s + l - 1) == demand.get(m, 0),
            name=f"demand_month_{m}"
        )

    # Linking constraints: for each length l, sum of x for that length <= M * y_l and >= y_l
    for l in contract_lengths:
        # compute sum of x for this length
        sum_for_length = gp.quicksum(x[(s, l)] for (s, ll) in feasible_pairs if ll == l)
        model.addConstr(sum_for_length <= M * y[l], name=f"link_upper_len_{l}")
        model.addConstr(sum_for_length >= y[l], name=f"link_lower_len_{l}")

    # Distinct lengths usage constraints
    model.addConstr(gp.quicksum(y[l] for l in contract_lengths) >= min_distinct)
    model.addConstr(gp.quicksum(y[l] for l in contract_lengths) <= max_distinct)

    # Mutually exclusive lengths: if any length in set {1,4} is used, the other must not be used
    if 1 in contract_lengths and 4 in contract_lengths:
        sum_len1 = gp.quicksum(x[(s, 1)] for (s, ll) in feasible_pairs if ll == 1)
        # Enforce: if y_4 = 1 then sum_len1 = 0
        model.addConstr(sum_len1 <= M * (1 - y[4]))
        # If y_4 = 0, sum_len1 can be positive; constraint above does not restrict otherwise.

    # Objective: minimize total rental cost
    objective = gp.quicksum(x[(s, l)] * fee_by_length[l] for (s, l) in feasible_pairs)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    # Prepare variables dict to return
    variables = {}
    for (s, l) in feasible_pairs:
        variables[f"x_{s}_{l}"] = x[(s, l)]
    for l in contract_lengths:
        variables[f"y_{l}"] = y[l]

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status
    stat = model.Status
    if stat == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    obj_val = float(model.ObjVal)

    # Helper to convert to int when appropriate
    def as_number(v):
        if v is None:
            return None
        val = float(v)
        if abs(val - round(val)) < 1e-6:
            return int(round(val))
        return val

    solution = {
        "x_1_1": as_number(variables["x_1_1"].X),
        "x_1_2": as_number(variables["x_1_2"].X),
        "x_1_3": as_number(variables["x_1_3"].X),
        "x_1_4": as_number(variables["x_1_4"].X),
        "x_2_1": as_number(variables["x_2_1"].X),
        "x_2_2": as_number(variables["x_2_2"].X),
        "x_2_3": as_number(variables["x_2_3"].X),
        "x_3_1": as_number(variables["x_3_1"].X),
        "x_3_2": as_number(variables["x_3_2"].X),
        "x_4_1": as_number(variables["x_4_1"].X),
        "y_1": as_number(variables["y_1"].X),
        "y_2": as_number(variables["y_2"].X),
        "y_3": as_number(variables["y_3"].X),
        "y_4": as_number(variables["y_4"].X),
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }