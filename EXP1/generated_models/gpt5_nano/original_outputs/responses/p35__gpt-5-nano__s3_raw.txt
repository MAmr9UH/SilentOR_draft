import gurobipy as gp

def build_model(data: dict) -> tuple:
    # Problem dimensions
    m = 2  # number of sources
    p = 2  # number of stations
    n = 2  # number of demands

    model = gp.Model()

    # Data extraction
    a = {1: float(data["supply"]["1"]), 2: float(data["supply"]["2"])}
    b = {1: float(data["demand"]["1"]), 2: float(data["demand"]["2"])}
    q = {1: float(data["station_capacity"]["1"]), 2: float(data["station_capacity"]["2"])}
    f = {1: float(data["fixed_cost"]["1"]), 2: float(data["fixed_cost"]["2"])}

    cost_x = {}
    for i in [1, 2]:
        for k in [1, 2]:
            key = f"{i},{k}"
            cost_x[(i, k)] = float(data["cost_source_station"][key])

    cost_z = {}
    for k in [1, 2]:
        for j in [1, 2]:
            key = f"{k},{j}"
            cost_z[(k, j)] = float(data["cost_station_demand"][key])

    # Decision variables
    x = {}
    for i in [1, 2]:
        for k in [1, 2]:
            x[(i, k)] = model.addVar(lb=0.0, name=f"x_{i}_{k}")

    z = {}
    for k in [1, 2]:
        for j in [1, 2]:
            z[(k, j)] = model.addVar(lb=0.0, name=f"z_{k}_{j}")

    y = {}
    for k in [1, 2]:
        y[k] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{k}")

    model.update()

    # Objective: minimize total cost
    transport_cost = gp.quicksum(cost_x[(i, k)] * x[(i, k)] for i in [1, 2] for k in [1, 2]) \
                     + gp.quicksum(cost_z[(k, j)] * z[(k, j)] for k in [1, 2] for j in [1, 2])
    fixed_cost = gp.quicksum(f[k] * y[k] for k in [1, 2])
    model.setObjective(transport_cost + fixed_cost, gp.GRB.MINIMIZE)

    # Constraints

    # Supply constraints: sum_k x_i_k <= a_i
    for i in [1, 2]:
        model.addConstr(gp.quicksum(x[(i, k)] for k in [1, 2]) <= a[i], name=f"Supply_{i}")

    # Demand constraints: sum_k z_k_j == b_j
    for j in [1, 2]:
        model.addConstr(gp.quicksum(z[(k, j)] for k in [1, 2]) == b[j], name=f"Demand_{j}")

    # Flow balance at each station: sum_i x_i_k == sum_j z_k_j
    for k in [1, 2]:
        model.addConstr(gp.quicksum(x[(i, k)] for i in [1, 2]) == gp.quicksum(z[(k, j)] for j in [1, 2]), name=f"Flow_{k}")

    # Capacity constraints with fixed costs: sum_i x_i_k <= q_k * y_k
    for k in [1, 2]:
        model.addConstr(gp.quicksum(x[(i, k)] for i in [1, 2]) <= q[k] * y[k], name=f"Cap_{k}")

    # Prepare variables dict with exact keys required
    variables = {
        "x_1_1": x[(1, 1)],
        "x_1_2": x[(1, 2)],
        "x_2_1": x[(2, 1)],
        "x_2_2": x[(2, 2)],
        "z_1_1": z[(1, 1)],
        "z_1_2": z[(1, 2)],
        "z_2_1": z[(2, 1)],
        "z_2_2": z[(2, 2)],
        "y_1": y[1],
        "y_2": y[2],
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    # Map status to string for output
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_num, str(status_num))

    obj_val = model.ObjVal
    objective = float(obj_val) if obj_val is not None else 0.0

    solution = {
        "x_1_1": float(variables["x_1_1"].X),
        "x_1_2": float(variables["x_1_2"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_2": float(variables["x_2_2"].X),
        "z_1_1": float(variables["z_1_1"].X),
        "z_1_2": float(variables["z_1_2"].X),
        "z_2_1": float(variables["z_2_1"].X),
        "z_2_2": float(variables["z_2_2"].X),
        "y_1": float(variables["y_1"].X),
        "y_2": float(variables["y_2"].X),
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }