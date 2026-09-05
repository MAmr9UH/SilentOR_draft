from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    model = Model()
    centers = data["centers"]      # e.g., ["c1","c2","c3","c4","c5"]
    stores = data["stores"]        # e.g., ["s1","s2",...,"s9"]

    opening_cost = data["fixed_opening_cost"]  # {"c1": 151000, ...}
    transport_cost = data["transport_cost"]     # {"c1": {"s1": 5, ...}, ...}
    demand = data["demand"]                     # {"s1": 739, ...}
    capacity = data["capacity"]                 # {"c1": 1825, ...}

    num_centers = len(centers)
    num_stores = len(stores)

    # Decision variables
    y = {}  # binary: center opened
    for i in range(1, num_centers + 1):
        key = f"y_c{i}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}  # shipments from center c to store s
    for i in range(1, num_centers + 1):
        for j in range(1, num_stores + 1):
            key = f"f_c{i}_s{j}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Constraints
    # 1) Demand satisfaction: sum_c f_c_s == demand_s for all s
    for j in range(1, num_stores + 1):
        demand_j = demand[f"s{j}"]
        model.addConstr(
            quicksum(f[f"f_c{i}_s{j}"] for i in range(1, num_centers + 1)) == demand_j,
            name=f"demand_s{j}"
        )

    # 2) Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for i in range(1, num_centers + 1):
        cap_i = capacity[f"c{i}"]
        model.addConstr(
            quicksum(f[f"f_c{i}_s{j}"] for j in range(1, num_stores + 1)) <= cap_i * y[f"y_c{i}"],
            name=f"cap_c{i}"
        )

    # Objective: minimize total fixed opening costs + transportation costs
    obj = quicksum(opening_cost[f"c{i}"] * y[f"y_c{i}"] for i in range(1, num_centers + 1)) \
          + quicksum(transport_cost[f"c{i}"][f"s{j}"] * f[f"f_c{i}_s{j}"]
                     for i in range(1, num_centers + 1)
                     for j in range(1, num_stores + 1))

    model.setObjective(obj, GRB.MINIMIZE)

    # Prepare return dictionary of all variable objects with exact keys
    variables = {}
    for i in range(1, num_centers + 1):
        variables[f"y_c{i}"] = y[f"y_c{i}"]
    for i in range(1, num_centers + 1):
        for j in range(1, num_stores + 1):
            variables[f"f_c{i}_s{j}"] = f[f"f_c{i}_s{j}"]

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

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

    objective = model.ObjVal

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }