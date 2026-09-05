import math
from gurobipy import Model, GRB, quicksum
from typing import Dict, Tuple

def build_model(data: dict) -> Tuple[Model, Dict[str, object]]:
    model = Model()

    # Basic data extraction
    max_vehicles = int(data.get("max_vehicles", len(data.get("vehicles", []))))
    vehicles = list(map(int, data.get("vehicles", [])))
    arcs_list = [tuple(map(int, arc)) for arc in data.get("arcs", [])]
    arcs_set = set(arcs_list)

    # Time windows, service durations, demands
    time_window = data.get("time_window", {})
    service_duration = data.get("service_duration", {})
    demand = data.get("demand", {})
    coordinates = data.get("coordinates", {})
    big_M = float(data.get("big_m", 100000.0))
    capacity = float(data.get("vehicle_capacity", 200.0))

    # Node sets
    customers = sorted([int(c) for c in data.get("customers", [])])
    depot = 0
    nodes = [depot] + customers

    # Helpers to access coordinates and distances
    def coord(n: int):
        return coordinates[str(n)]
    def dist(i: int, j: int) -> float:
        xi, yi = coord(i)
        xj, yj = coord(j)
        return math.hypot(xi - xj, yi - yj)

    # Service duration for each node (0 has 0)
    s = {i: float(service_duration.get(str(i), 0)) for i in nodes}
    # Time window bounds
    a = {i: float(time_window.get(str(i), [0, 0])[0]) for i in nodes}
    b = {i: float(time_window.get(str(i), [0, 0])[1]) for i in nodes}
    # Demands
    d = {i: float(demand.get(str(i), 0)) for i in customers}
    d[0] = 0.0

    # Precompute inbound/outbound arcs per node
    inbound = {i: [] for i in nodes}
    outbound = {i: [] for i in nodes}
    for (p, q) in arcs_list:
        inbound[q].append(p)
        outbound[p].append(q)

    # Decision variables: x_v{k}_{p}_{i} for each arc (p,i) and vehicle k
    variables: Dict[str, object] = {}

    def x_key(k: int, p: int, i: int) -> str:
        return f"x_v{k}_{p}_{i}"

    # Create arc variables
    for k in vehicles:
        for (p, i) in arcs_list:
            key = x_key(k, p, i)
            v = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = v

    # Time variables t_v{k}_{i} for i in 1..20 (customers)
    def t_key(k: int, i: int) -> str:
        return f"t_v{k}_{i}"
    for k in vehicles:
        for i in customers:
            key = t_key(k, i)
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize total travel distance
    obj = 0.0
    for k in vehicles:
        for (p, i) in arcs_list:
            v = variables[x_key(k, p, i)]
            obj += v * dist(p, i)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1) Each customer is served exactly once (sum over vehicles and incoming arcs)
    for i in customers:
        inbound_sum = quicksum( variables[x_key(k, p, i)] for k in vehicles for p in inbound[i] )
        # In case of any mis-spec, ensure equality to 1
        model.addConstr(inbound_sum == 1)

    # 2) Flow conservation for each vehicle on each customer (except depot)
    for k in vehicles:
        for i in customers:
            sum_out = quicksum( variables[x_key(k, i, j)] for j in outbound[i] )
            sum_in = quicksum( variables[x_key(k, p, i)] for p in inbound[i] )
            model.addConstr(sum_out == sum_in)

    # 3) Depot flow balance per vehicle (depart from depot equals return to depot)
    for k in vehicles:
        dep_out = quicksum( variables[x_key(k, depot, j)] for j in outbound[depot] )
        dep_in  = quicksum( variables[x_key(k, i, depot)] for i in inbound[depot] )
        model.addConstr(dep_out == dep_in)

    # 4) Depot usage limit (at most max_vehicles depart)
    total_departures = quicksum( variables[x_key(k, depot, j)] for k in vehicles for j in outbound[depot] )
    model.addConstr(total_departures <= max_vehicles)

    # 5) Per-vehicle capacity constraints
    # For each vehicle k: sum of demands of served customers <= capacity if vehicle is used
    for k in vehicles:
        lhs = quicksum(
            d[i] * quicksum( variables[x_key(k, p, i)] for p in inbound[i] )
            for i in customers
        )
        rhs = capacity * quicksum( variables[x_key(k, depot, i)] for i in outbound[depot] )
        model.addConstr(lhs <= rhs)

    # 6) Time window propagation (big-M) and depot start constraints
    # For each vehicle k and customer i: arrival time must be within window if visited
    for k in vehicles:
        for i in customers:
            sum_in_i = quicksum( variables[x_key(k, p, i)] for p in inbound[i] )
            t_ki = variables[t_key(k, i)]
            model.addConstr(t_ki >= a[i] - big_M * (1 - sum_in_i))
            model.addConstr(t_ki <= b[i] + big_M * (1 - sum_in_i))

    # Arc-based time propagation
    # For arcs from non-depot nodes: t_j >= t_i + s_i + dist(i,j) - M*(1 - x_k_i_j)
    for k in vehicles:
        for (i, j) in arcs_list:
            if i != depot:
                t_j = variables[t_key(k, j)]
                t_i = variables[t_key(k, i)]
                x_ij = variables[x_key(k, i, j)]
                model.addConstr(t_j >= t_i + s[i] + dist(i, j) - big_M * (1 - x_ij))
        # For arcs from depot (0 -> j): enforce start time constraints
        for j in outbound[depot]:
            if (depot, j) in arcs_set:
                t_j = variables[t_key(k, j)]
                x_0j = variables[x_key(k, depot, j)]
                model.addConstr(t_j >= a[j] - big_M * (1 - x_0j))
                model.addConstr(t_j <= b[j] + big_M * (1 - x_0j))

    model.update()
    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "Optimal"
    elif status == GRB.TIME_LIMIT:
        status_str = "TimeLimit"
    elif status == GRB.INFEASIBLE:
        status_str = "Infeasible"
    elif status == GRB.UNBOUNDED:
        status_str = "Unbounded"
    elif status == GRB.INF_OR_UNBD:
        status_str = "InfOrUnbd"
    else:
        status_str = str(status)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Collect solution values for all keys
    solution = {}
    for key, var in variables.items():
        try:
            solution[key] = float(var.X)
        except:
            solution[key] = None

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }