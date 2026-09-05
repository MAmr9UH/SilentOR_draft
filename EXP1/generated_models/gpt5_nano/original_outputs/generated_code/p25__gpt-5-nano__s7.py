import math
from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    # Parse data
    depot = int(data["depot"])
    customers = [int(c) for c in data["customers"]]
    vehicles = [int(v) for v in data["vehicles"]]
    max_vehicles = int(data["max_vehicles"])
    vehicle_capacity = int(data["vehicle_capacity"])
    big_m = int(data["big_m"])
    # Coordinates
    coords_raw = data["coordinates"]
    coords = {}
    for k, v in coords_raw.items():
        coords[int(k)] = (float(v[0]), float(v[1]))
    # Distances
    def dist(a: int, b: int) -> float:
        x1, y1 = coords[a]
        x2, y2 = coords[b]
        return math.hypot(x1 - x2, y1 - y2)
    # Time windows
    # Initialize with depot
    start_time = {0: 0}
    end_time = {0: int(data["time_window"][str(depot)][1]) if str(depot) in data["time_window"] and isinstance(data["time_window"][str(depot)], list) else 1236}
    # Fill from data
    for k, v in data["time_window"].items():
        idx = int(k)
        start_time[idx] = int(v[0])
        end_time[idx] = int(v[1])
    # Service duration
    service_duration = {0: 0}
    for c in customers:
        service_duration[c] = int(data["service_duration"][str(c)])
    # Demands
    demand = {0: 0}
    for c in customers:
        demand[c] = int(data["demand"][str(c)])
    # Arcs
    arcs = [(int(a), int(b)) for (a, b) in data["arcs"]]
    # Precompute distances on arcs
    dist_on_arc = {}
    for (i, j) in arcs:
        dist_on_arc[(i, j)] = dist(i, j)
    # Inbound arcs for each customer
    inbound_by_j = {c: [] for c in customers}
    for (i, j) in arcs:
        if j in inbound_by_j:
            inbound_by_j[j].append(i)
    # Build model
    model = Model()
    model.setParam("OutputFlag", 0)

    # Variables dictionary to return
    variables = {}

    # Arc variables: x_v_i_j for each vehicle v and each arc (i,j)
    # Keys: "x_v{v}_{i}_{j}"
    for v in vehicles:
        for (i, j) in arcs:
            key = f"x_v{v}_{i}_{j}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Time variables: t_v_j for each vehicle v and customer j
    # Keys: "t_v{v}_{j}"
    for v in vehicles:
        for j in customers:
            key = f"t_v{v}_{j}"
            # Domain within its window; allow some flexibility
            lb = start_time[j]
            ub = end_time[j]
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=lb, ub=ub, name=key)

    model.update()

    # Objective: minimize total travel distance
    obj = 0.0
    for v in vehicles:
        for (i, j) in arcs:
            obj += dist_on_arc[(i, j)] * variables[f"x_v{v}_{i}_{j}"]
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1) Each customer is entered exactly once (one inbound arc across all vehicles)
    for j in customers:
        model.addConstr(
            quicksum(variables[f"x_v{v}_{i}_{j}"] for v in vehicles for i in inbound_by_j[j]) == 1
        )

    # 2) Flow conservation at depot: departures equal arrivals; at most max_vehicles departures
    dep_out = quicksum(variables[f"x_v{v}_0_{j}"] for v in vehicles for j in customers if (0, j) in arcs)
    dep_in = quicksum(variables[f"x_v{v}_{i}_0"] for v in vehicles for i in customers if (i, 0) in arcs)
    model.addConstr(dep_out == dep_in)
    model.addConstr(dep_out <= max_vehicles)

    # 3) Vehicle capacity constraints
    for v in vehicles:
        capacity_load = quicksum(
            demand[j] * quicksum(variables[f"x_v{v}_{i}_{j}"] for i in inbound_by_j[j])
            for j in customers
        )
        model.addConstr(capacity_load <= vehicle_capacity)

    # 4) Time windows and time propagation (big-M)
    for v in vehicles:
        # Inbound time window consistency
        for j in customers:
            sum_in = quicksum(variables[f"x_v{v}_{i}_{j}"] for i in inbound_by_j[j])
            tvar = variables[f"t_v{v}_{j}"]
            model.addConstr(tvar >= start_time[j] - big_m * (1 - sum_in))
            model.addConstr(tvar <= end_time[j] + big_m * (1 - sum_in))
        # Time propagation along arcs
        for (i, j) in arcs:
            xvar = variables[f"x_v{v}_{i}_{j}"]
            tj = variables[f"t_v{v}_{j}"]
            ti = variables[f"t_v{v}_{i}"]
            if i != 0 and j != 0:
                model.addConstr(
                    tj - ti >= service_duration[i] + dist_on_arc[(i, j)] - big_m * (1 - xvar)
                )
            elif i == 0 and j != 0:
                # From depot to first customer
                model.addConstr(
                    tj >= dist(0, j) - big_m * (1 - xvar)
                )
            # If j == 0, no time propagation constraint needed (return to depot)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD"
    }
    status = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal) if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) else float('inf')

    # Build solution dict with all required keys
    solution = {}
    for key, var in variables.items():
        # For linear vars, use .X
        try:
            solution[key] = float(var.X)
        except Exception:
            # If var is a dict (shouldn't happen here), flatten
            solution[key] = 0.0

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number"},
            "solution": {
                "type": "object",
                "required": list(variables.keys()),
            },
        },
    }

    # Prepare final dict matching the required schema
    final = {
        "status": status,
        "objective": objective,
        "solution": solution
    }

    return final