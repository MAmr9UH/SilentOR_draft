import math
from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    # Initialize model
    m = Model()
    m.setParam('OutputFlag', 0)

    # Basic data
    depot = data["depot"]
    customers = data["customers"]  # list of ints
    vehicles = data["vehicles"]    # list of ints
    max_vehicles = data["max_vehicles"]
    capacity = data["vehicle_capacity"]

    arcs = data["arcs"]  # list of (i,j)
    arc_set = set(tuple(a) for a in arcs)

    # Distances
    dist = {}
    for key, val in data["distance"].items():
        i_str, j_str = key.split(",")
        dist[(int(i_str), int(j_str))] = val

    # Time windows
    TW_start = {}
    TW_end = {}
    TW = data["time_window"]  # dict with string keys
    TW_start[0], TW_end[0] = TW["0"][0], TW["0"][1]
    for c in customers:
        TW_start[c], TW_end[c] = TW[str(c)][0], TW[str(c)][1]

    # Service durations
    service = {0: 0}
    for c in customers:
        service[c] = data["service_duration"][str(c)]

    big_M = data["big_m"]

    # Decision variables
    x = {}  # (v,i,j) -> binary var
    variables = {}

    for v in vehicles:
        for (i, j) in arc_set:
            key = f"x_v{v}_{i}_{j}"
            x[(v, i, j)] = m.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = x[(v, i, j)]

    # Time variables: t_v_i for each vehicle and customer i>0
    t = {}
    for v in vehicles:
        for i in customers:
            key = f"t_v{v}_{i}"
            t[(v, i)] = m.addVar(vtype=GRB.CONTINUOUS, name=key)
            variables[key] = t[(v, i)]

    m.update()

    # Constraints

    # 1) Each customer has exactly one incoming arc
    for i in customers:
        inbound = []
        for v in vehicles:
            for (a, b) in arc_set:
                if b == i:
                    inbound.append(x[(v, a, b)])
        m.addConstr(quicksum(inbound) == 1)

    # 2) Each customer has exactly one outgoing arc
    for i in customers:
        outbound = []
        for v in vehicles:
            for (a, b) in arc_set:
                if a == i:
                    outbound.append(x[(v, a, b)])
        m.addConstr(quicksum(outbound) == 1)

    # 3) Depot constraint: total departures from depot <= max_vehicles
    depot_out = []
    for v in vehicles:
        for (a, b) in arc_set:
            if a == 0:
                depot_out.append(x[(v, a, b)])
    m.addConstr(quicksum(depot_out) <= max_vehicles)

    # 4) Vehicle capacity constraints
    for v in vehicles:
        cap_expr = 0
        for i in customers:
            demand_i = data["demand"][str(i)]
            cap_expr += demand_i * quicksum(x[(v, i, j)] for (a, b) in arc_set if a == i)
        m.addConstr(cap_expr <= capacity)

    # 5) Time window constraints (for all vehicle-customer combinations)
    for v in vehicles:
        for i in customers:
            m.addConstr(t[(v, i)] >= TW_start[i])
            m.addConstr(t[(v, i)] <= TW_end[i])

    # 6) Time propagation (big-M)
    for v in vehicles:
        for (i, j) in arc_set:
            if i == 0:
                # From depot to j
                m.addConstr(t[(v, j)] >= dist[(0, j)] - big_M * (1 - x[(v, 0, j)]))
            else:
                # From i to j
                m.addConstr(t[(v, j)] >= t[(v, i)] + service[i] + dist[(i, j)] - big_M * (1 - x[(v, i, j)]))

    # Objective: minimize total travel distance
    obj = quicksum(dist[(i, j)] * x[(v, i, j)]
                   for v in vehicles
                   for (i, j) in arc_set)
    m.setObjective(obj, GRB.MINIMIZE)

    return m, variables


def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_text = "OPTIMAL"
    elif stat == GRB.TIME_LIMIT:
        status_text = "TIME_LIMIT"
    elif stat == GRB.INFEASIBLE:
        status_text = "INFEASIBLE"
    elif stat == GRB.INF_OR_UNBD:
        status_text = "INF_OR_UNBD"
    elif stat == GRB.UNBOUNDED:
        status_text = "UNBOUNDED"
    else:
        status_text = str(stat)

    objective_value = float(model.ObjVal)

    # Build solution dictionary with all required keys
    solution = {}

    # Arc variables keys
    for v in data["vehicles"]:
        for (i, j) in data["arcs"]:
            key = f"x_v{v}_{i}_{j}"
            if key in variables:
                solution[key] = float(variables[key].X)

    # Time variables keys
    for v in data["vehicles"]:
        for i in data["customers"]:
            key = f"t_v{v}_{i}"
            if key in variables:
                solution[key] = float(variables[key].X)

    return {
        "status": status_text,
        "objective": objective_value,
        "solution": solution
    }