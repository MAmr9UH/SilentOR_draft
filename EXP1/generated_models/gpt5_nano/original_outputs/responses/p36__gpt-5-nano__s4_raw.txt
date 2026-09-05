import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    feasible = data["feasible_start_length_pairs"]
    # Create x_s_l variables for each feasible (start, length)
    x = {}
    for (s, l) in feasible:
        x[(s, l)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{s}_{l}")

    # Create y_l binary variables for each length
    y = {}
    for l in [1, 2, 3, 4]:
        y[l] = model.addVar(vtype=GRB.BINARY, name=f"y_{l}")

    model.update()

    # Demand constraints: for each month m, sum of covering contracts equals demand
    demands = data["demand_100sqm"]
    for m in range(1, 5):
        demand_m = int(demands[str(m)])
        expr = gp.quicksum(x[(s, l)] for (s, l) in feasible if s <= m <= s + l - 1)
        model.addConstr(expr == demand_m, name=f"demand_month_{m}")

    # Linking and exclusive constraints for lengths
    BIG = 1000
    for l in [1, 2, 3, 4]:
        sum_xl = gp.quicksum(x[(s, l)] for (s, ll) in feasible if ll == l)
        model.addConstr(sum_xl <= BIG * y[l], name=f"link_upper_len_{l}")
        model.addConstr(sum_xl >= y[l], name=f"link_lower_len_{l}")

    # If any 4-month contract is used, no 1-month contracts can be used
    sum_x1 = gp.quicksum(x[(s, 1)] for (s, ll) in feasible if ll == 1)
    model.addConstr(sum_x1 <= BIG * (1 - y[4]), name="no1_if_any4")

    # Distinct lengths constraints
    min_dist = data["min_distinct_lengths"]
    max_dist = data["max_distinct_lengths"]
    model.addConstr(gp.quicksum(y[l] for l in [1, 2, 3, 4]) >= min_dist, name="min_distinct_lengths")
    model.addConstr(gp.quicksum(y[l] for l in [1, 2, 3, 4]) <= max_dist, name="max_distinct_lengths")

    # Objective: minimize total rental cost
    cost_by_len = data["fee_per_100sqm_by_length"]
    cost = {1: int(cost_by_len["1"]), 2: int(cost_by_len["2"]),
            3: int(cost_by_len["3"]), 4: int(cost_by_len["4"])}
    objective = gp.quicksum(x[(s, l)] * cost[l] for (s, l) in feasible)
    model.setObjective(objective, GRB.MINIMIZE)

    variables = {
        "x_1_1": x[(1, 1)],
        "x_1_2": x[(1, 2)],
        "x_1_3": x[(1, 3)],
        "x_1_4": x[(1, 4)],
        "x_2_1": x[(2, 1)],
        "x_2_2": x[(2, 2)],
        "x_2_3": x[(2, 3)],
        "x_3_1": x[(3, 1)],
        "x_3_2": x[(3, 2)],
        "x_4_1": x[(4, 1)],
        "y_1": y[1],
        "y_2": y[2],
        "y_3": y[3],
        "y_4": y[4]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

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

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    keys = ["x_1_1","x_1_2","x_1_3","x_1_4","x_2_1","x_2_2","x_2_3","x_3_1","x_3_2","x_4_1","y_1","y_2","y_3","y_4"]
    solution = {}
    for k in keys:
        solution[k] = float(variables[k].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }