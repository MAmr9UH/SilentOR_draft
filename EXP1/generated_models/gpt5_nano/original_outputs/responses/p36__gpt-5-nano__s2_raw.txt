import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Feasible start/length pairs
    feasible_pairs = [tuple(p) for p in data["feasible_start_length_pairs"]]
    feasible_set = set(feasible_pairs)

    # Demand per month (convert keys to int)
    demand = {int(k): int(v) for k, v in data["demand_100sqm"].items()}

    # Total potential maximum contracts (upper bound for linking constraints)
    total_demand = sum(demand.values())
    M = int(total_demand)  # safe upper bound

    # Decision variables: x_s_l for each feasible pair
    x_vars = {}
    for (s, l) in feasible_pairs:
        var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{s}_{l}")
        x_vars[(s, l)] = var

    # Binary variables: y_l for each contract length
    y_vars = {}
    for l in data["contract_lengths"]:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{l}")
        y_vars[l] = var

    model.update()

    # Objective: minimize total rental cost
    fees_by_length = {int(k): int(v) for k, v in data["fee_per_100sqm_by_length"].items()}
    obj_expr = gp.quicksum(x_vars[(s, l)] * fees_by_length[l] for (s, l) in feasible_pairs)
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # Demand constraints: exact equality per month
    for m in range(1, 5):
        month_sum = gp.quicksum(x_vars[(s, l)]
                                for (s, l) in feasible_pairs if s <= m <= s + l - 1)
        model.addConstr(month_sum == demand[m], name=f"demand_m{m}")

    # Linking constraints: x_s_l <= M * y_l
    for (s, l) in feasible_pairs:
        model.addConstr(x_vars[(s, l)] <= M * y_vars[l], name=f"link_len_{l}_start_{s}")

    # At least two different contract lengths must be used
    model.addConstr(gp.quicksum(y_vars[l] for l in data["contract_lengths"]) >= 2, name="min_two_lengths")

    # Distinct lengths used cannot exceed 3
    model.addConstr(gp.quicksum(y_vars[l] for l in data["contract_lengths"]) <= 3, name="max_three_lengths")

    # If a 4-month contract is chosen, then no 1-month contracts may be chosen
    # (Only (1,4) is feasible for length 4)
    if (1, 4) in feasible_set:
        for s in range(1, 5):
            if (s, 1) in feasible_set:
                model.addConstr(x_vars[(s, 1)] <= M * (1 - y_vars[4]),
                                name=f"no1_if4_start_{s}")

    # Return model and a dict of all variables with required keys
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
        "y_4": y_vars[4]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
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

    objective = float(model.ObjVal)

    # Build solution dict with required keys in specified order
    keys_order = [
        "x_1_1","x_1_2","x_1_3","x_1_4",
        "x_2_1","x_2_2","x_2_3",
        "x_3_1","x_3_2",
        "x_4_1",
        "y_1","y_2","y_3","y_4"
    ]
    solution = {}
    for k in keys_order:
        solution[k] = float(variables[k].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }