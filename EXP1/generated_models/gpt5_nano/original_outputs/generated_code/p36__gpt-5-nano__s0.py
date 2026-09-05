import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    model = gp.Model()
    # Data extraction
    months = [int(m) for m in data["months"]]
    demand_dict = {int(k): int(v) for k, v in data["demand_100sqm"].items()}
    feasible_pairs = [tuple(pair) for pair in data["feasible_start_length_pairs"]]
    contract_lengths = [int(l) for l in data["contract_lengths"]]
    fees = {int(k): int(v) for k, v in data["fee_per_100sqm_by_length"].items()}
    min_distinct = int(data["min_distinct_lengths"])
    max_distinct = int(data["max_distinct_lengths"])

    BIG = 1000000

    # Decision variables
    x_vars = {}
    for (s, l) in feasible_pairs:
        var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x_vars[(s, l)] = var

    y_vars = {}
    for l in contract_lengths:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{l}")
        y_vars[l] = var

    model.update()

    # Demand constraints: for each month m, sum of active contracts covering m must equal demand
    for m in months:
        expr = quicksum(x_vars[(s, l)]
                        for (s, l) in feasible_pairs
                        if s <= m <= s + l - 1)
        model.addConstr(expr == demand_dict[m], name=f"demand_{m}")

    # Link contracts to length usage: if any contract of length l is used, y_l = 1
    for l in [1, 2, 3, 4]:
        expr = quicksum(x_vars[(s, l)] for (s, l2) in feasible_pairs if l2 == l)
        model.addConstr(expr >= y_vars[l], name=f"use_len_ge_{l}")
        model.addConstr(expr <= BIG * y_vars[l], name=f"use_len_le_{l}")

    # Distinct lengths constraints
    model.addConstr(quicksum(y_vars[l] for l in [1, 2, 3, 4]) >= min_distinct, name="min_distinct_lengths")
    model.addConstr(quicksum(y_vars[l] for l in [1, 2, 3, 4]) <= max_distinct, name="max_distinct_lengths")

    # If a 4-month contract is chosen, no 1-month contracts may be chosen
    expr_1m = quicksum(x_vars[(s, 1)] for s in [1, 2, 3, 4] if (s, 1) in x_vars)
    model.addConstr(expr_1m <= BIG * (1 - y_vars[4]), name="no_1month_if_4month")

    # Objective: minimize total rental cost
    obj = quicksum(x_vars[(s, l)] * fees[l] for (s, l) in feasible_pairs)
    model.setObjective(obj, GRB.MINIMIZE)

    variables = {
        "x_1_1": x_vars[(1, 1)],
        "x_1_2": x_vars[(1, 2)],
        "x_1_3": x_vars[(1, 3)],
        "x_1_4": x_vars[(1, 4)],
        "x_2_1": x_vars[(2, 1)],
        "x_2_2": x_vars[(2, 2)],
        "x_2_3": x_vars[(2, 3)],
        "x_3_1": x_vars[(3, 1)],
        "x_3_2": x_vars[(3, 2)],
        "x_4_1": x_vars[(4, 1)],
        "y_1": y_vars[1],
        "y_2": y_vars[2],
        "y_3": y_vars[3],
        "y_4": y_vars[4],
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    # Ensure model is updated before reading values
    model.update()
    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {
        "x_1_1": float(variables["x_1_1"].X),
        "x_1_2": float(variables["x_1_2"].X),
        "x_1_3": float(variables["x_1_3"].X),
        "x_1_4": float(variables["x_1_4"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_2": float(variables["x_2_2"].X),
        "x_2_3": float(variables["x_2_3"].X),
        "x_3_1": float(variables["x_3_1"].X),
        "x_3_2": float(variables["x_3_2"].X),
        "x_4_1": float(variables["x_4_1"].X),
        "y_1": float(variables["y_1"].X),
        "y_2": float(variables["y_2"].X),
        "y_3": float(variables["y_3"].X),
        "y_4": float(variables["y_4"].X),
    }

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }