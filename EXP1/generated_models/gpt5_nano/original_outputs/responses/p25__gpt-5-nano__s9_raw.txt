import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Prepare data
    depot = data["depot"]
    customers = data["customers"]  # list of customer indices (ints)
    N = len(customers)  # should be 20
    vehicles = data["vehicles"]  # list of vehicle indices (ints)
    V = len(vehicles)  # up to 5
    capacity = data["vehicle_capacity"]
    dist = data["distance"]  # dict with keys like "0,1" or "1,0"
    coords = data["coordinates"]
    demand = {int(k): int(v) for k, v in data["demand"].items()}
    a_win = {}
    b_win = {}
    for j in customers:
        w = data["time_window"][str(j)]
        a_win[j] = w[0]
        b_win[j] = w[1]
    # Service durations
    service = {}
    for k, v in data["service_duration"].items():
        service[int(k)] = v
    big_M = data.get("big_m", 1000000)
    # Arc list
    arc_list = [(int(i), int(j)) for (i, j) in data["arcs"]]
    arc_set = set(arc_list)

    model = gp.Model()

    # Decision variables: x_v_i_j for each vehicle v and each arc (i,j)
    x = {}
    for v in vehicles:
        for (i, j) in arc_list:
            name = f"x_v{v}_{i}_{j}"
            x[(v, i, j)] = model.addVar(vtype=GRB.BINARY, name=name)

    # Time variables t_v_j for each vehicle v and customer j
    t = {}
    for v in vehicles:
        for j in customers:
            name = f"t_v{v}_{j}"
            t[(v, j)] = model.addVar(vtype=GRB.CONTINUOUS,
                                      lb=a_win[j],
                                      ub=b_win[j],
                                      name=name)

    model.update()

    # Objective: minimize total travel distance
    obj = gp.quicksum(dist[f"{i},{j}"] * x[(v, i, j)]
                      for v in vehicles
                      for (i, j) in arc_list)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1) Each customer j is entered exactly once
    for j in customers:
        expr = gp.quicksum(x[(v, i, j)]
                           for v in vehicles
                           for (i, jj) in arc_list
                           if jj == j and (v, i, j) in x)
        model.addConstr(expr == 1, name=f"visit_once_{j}")

    # 2) Depot departure: each vehicle departs from depot at most once
    for v in vehicles:
        expr = gp.quicksum(x[(v, 0, j)]
                           for j in customers if (0, j) in arc_set)
        model.addConstr(expr <= 1, name=f"depart_depot_{v}")

    # 3) Depot return: each vehicle returns to depot at most once
    for v in vehicles:
        expr = gp.quicksum(x[(v, i, 0)]
                           for i in customers if (i, 0) in arc_set)
        model.addConstr(expr <= 1, name=f"return_depot_{v}")

    # 4) Capacity constraints
    for v in vehicles:
        load = gp.quicksum(demand[j] * x[(v, i, j)]
                           for j in customers
                           for i in range(0, max([a for (a,b) in arc_list] + [0]) + 1)
                           if (i, j) in arc_set)
        model.addConstr(load <= capacity, name=f"capacity_{v}")

    # 5) Time window propagation (big-M)
    # For arcs i->j with j != 0
    for v in vehicles:
        for (i, j) in arc_list:
            if j == 0:
                continue  # no time variable for depot
            xvar = x[(v, i, j)]
            tij = t[(v, j)]
            dist_ij = dist.get(f"{i},{j}", 0.0)

            if i == 0:
                # From depot to j
                # tij >= distance from depot to j
                model.addConstr(tij >= dist_ij - big_M * (1 - xvar),
                                name=f"time_dep_{v}_{j}")
            else:
                # From i (customer) to j
                dist_ij = dist.get(f"{i},{j}", 0.0)
                somelength = service.get(i, 0)
                model.addConstr(tij >= t[(v, i)] + somelength + dist_ij - big_M * (1 - xvar),
                                name=f"time_move_{v}_{i}_{j}")

    # Time window hard bounds (already set as lb/ub for t_v_j)
    # (No extra constraints needed beyond lb/ub and propagation)

    model.update()
    variables = {}
    # Pack variables into the required flat keys
    for v in vehicles:
        for (i, j) in arc_list:
            key = f"x_v{v}_{i}_{j}"
            variables[key] = x[(v, i, j)]
    for v in vehicles:
        for j in customers:
            key = f"t_v{v}_{j}"
            variables[key] = t[(v, j)]

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.setParam('OutputFlag', 0)
    model.optimize()

    status = model.Status
    status_str = "OPTIMAL" if status == GRB.OPTIMAL else str(status)

    obj_val = None
    if status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.SUBOPTIMAL, GRB.INFEASIBLE, GRB.INF_OR_UNBD):
        obj_val = float(model.ObjVal)

    # Build solution dict with all variable values
    solution = {}
    for key, var in variables.items():
        try:
            solution[key] = float(var.X)
        except Exception:
            solution[key] = None

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }