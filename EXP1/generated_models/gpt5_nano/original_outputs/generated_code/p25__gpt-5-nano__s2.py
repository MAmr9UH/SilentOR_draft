import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict):
    model = gp.Model("VRP_TW")

    # Helper data
    coords = data["coordinates"]  # dict of str -> [x,y]
    def coord(n):
        return coords[str(n)]
    def dist(i, j):
        xi, yi = coord(i)
        xj, yj = coord(j)
        return math.hypot(xi - xj, yi - yj)

    # Node set
    nodes = list(range(0, 21))  # 0 is depot, 1..20 customers
    arcs = data["arcs"]
    arcs_set = set((a, b) for a, b in arcs)

    vehicles = [1, 2, 3, 4, 5]
    # Variables container: keys must match exactly the required strings
    variables = {}

    # x_v_i_j variables for each vehicle and arc
    for v in vehicles:
        for (i, j) in arcs:
            key = f"x_v{v}_{i}_{j}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # t_v_j variables for each vehicle and customer (j=1..20)
    service_duration = {0: 0}
    for j in range(1, 21):
        service_duration[j] = 90  # fixed service duration
        key = f"t_v{v}_{j}" if False else None  # placeholder to satisfy linter; actual keys below
    for v in vehicles:
        for j in range(1, 21):
            key = f"t_v{v}_{j}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)

    # y_v variables: which vehicles are used (not part of the final solution dict per spec)
    y_vars = {}
    for v in vehicles:
        y_vars[v] = model.addVar(vtype=GRB.BINARY, name=f"y_v{v}")

    # Objective: minimize total travel distance
    obj = gp.quicksum(dist(i, j) * variables[f"x_v{v}_{i}_{j}"] for v in vehicles for (i, j) in arcs)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # Each customer has exactly one incoming arc
    for j in range(1, 21):
        inflow = gp.quicksum(variables[f"x_v{v}_{i}_{j}"] for v in vehicles for i in nodes if (i, j) in arcs_set)
        model.addConstr(inflow == 1)

    # Each customer has exactly one outgoing arc
    for j in range(1, 21):
        outflow = gp.quicksum(variables[f"x_v{v}_{j}_{k}"] for v in vehicles for k in nodes if (j, k) in arcs_set)
        model.addConstr(outflow == 1)

    # Depot flow constraints: each used vehicle starts and ends at depot
    for v in vehicles:
        dep_out = gp.quicksum(variables[f"x_v{v}_0_{j}"] for j in range(1, 21) if (0, j) in arcs_set)
        dep_in  = gp.quicksum(variables[f"x_v{v}_{i}_0"] for i in range(1, 21) if (i, 0) in arcs_set)
        model.addConstr(dep_out == y_vars[v])
        model.addConstr(dep_in  == y_vars[v])

    # Limit number of vehicles used
    model.addConstr(gp.quicksum(y_vars[v] for v in vehicles) <= data["max_vehicles"])

    # Vehicle capacity constraints
    capacity = data["vehicle_capacity"]
    demand = data["demand"]
    for v in vehicles:
        cap_expr = gp.quicksum(
            demand[str(j)] * gp.quicksum(variables[f"x_v{v}_{i}_{j}"] for i in nodes if (i, j) in arcs_set)
            for j in range(1, 21)
        )
        model.addConstr(cap_expr <= capacity)

    # Time window constraints and propagation
    M = data.get("big_m", 2000)

    # Time window bounds for each (vehicle, customer)
    for v in vehicles:
        for j in range(1, 21):
            t_var = variables[f"t_v{v}_{j}"]
            start_j, end_j = data["time_window"][str(j)]
            model.addConstr(t_var >= start_j)
            model.addConstr(t_var <= end_j)

    # Time propagation along arcs (excluding arcs into depot)
    for v in vehicles:
        for (i, j) in arcs:
            if j == 0:
                continue  # skip arcs ending at depot for time propagation
            t_j = variables[f"t_v{v}_{j}"]
            if i == 0:
                x_0j = variables[f"x_v{v}_0_{j}"]
                model.addConstr(t_j >= dist(0, j) - M * (1 - x_0j))
            else:
                x_ij = variables[f"x_v{v}_{i}_{j}"]
                t_i = variables[f"t_v{v}_{i}"]
                model.addConstr(t_j >= t_i + service_duration[i] + dist(i, j) - M * (1 - x_ij))

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    # Optional: silence solver output for cleaner results
    model.setParam("OutputFlag", 0)
    model.optimize()

    # Status mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    st = model.Status
    status = status_map.get(st, "UNKNOWN")
    objective = model.ObjVal if st in (GRB.OPTIMAL, GRB.TIME_LIMIT) else None

    # Build solution dictionary with exactly the required keys
    solution = {}

    # x variables values
    for (key, var) in variables.items():
        if key.startswith("x_v"):
            solution[key] = int(round(var.X))

    # t variables values
    for (key, var) in variables.items():
        if key.startswith("t_v"):
            solution[key] = float(var.X)

    return {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "status": status,
        "objective": objective,
        "solution": solution
    }