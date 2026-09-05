import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model("two_stage_fixed_cost")

    # Parse data
    sources = [int(x) for x in data["sources"]]
    stations = [int(x) for x in data["stations"]]
    demands = [int(x) for x in data["demands"]]

    a = {int(k): float(v) for k, v in data["supply"].items()}
    b = {int(k): float(v) for k, v in data["demand"].items()}
    q = {int(k): float(v) for k, v in data["station_capacity"].items()}
    f = {int(k): float(v) for k, v in data["fixed_cost"].items()}

    c_src = {}
    for key, val in data["cost_source_station"].items():
        i, k = map(int, key.split(","))
        c_src[(i, k)] = float(val)

    c_dst = {}
    for key, val in data["cost_station_demand"].items():
        k, j = map(int, key.split(","))
        c_dst[(k, j)] = float(val)

    # Decision variables
    x = {}
    for i in sources:
        for k in stations:
            x[(i, k)] = m.addVar(lb=0.0, name=f"x_{i}_{k}")

    z = {}
    for k in stations:
        for j in demands:
            z[(k, j)] = m.addVar(lb=0.0, name=f"z_{k}_{j}")

    y = {}
    for k in stations:
        y[k] = m.addVar(vtype=GRB.BINARY, name=f"y_{k}")

    m.update()

    # Constraints
    # 1) Supply constraints: sum_k x[i,k] <= a_i
    for i in sources:
        m.addConstr(gp.quicksum(x[(i, k)] for k in stations) <= a[i], name=f"Supply_{i}")

    # 2) Demand constraints: sum_k z[k,j] >= b_j
    for j in demands:
        m.addConstr(gp.quicksum(z[(k, j)] for k in stations) >= b[j], name=f"Demand_{j}")

    # 3) Flow conservation at each station: sum_i x[i,k] == sum_j z[k,j]
    for k in stations:
        m.addConstr(gp.quicksum(x[(i, k)] for i in sources) == gp.quicksum(z[(k, j)] for j in demands), name=f"Flow_{k}")

    # 4) Capacity with fixed cost linking: sum_i x[i,k] <= q_k * y_k
    for k in stations:
        m.addConstr(gp.quicksum(x[(i, k)] for i in sources) <= q[k] * y[k], name=f"Cap_{k}")

    # Objective: minimize transportation costs + fixed costs
    objective = gp.quicksum(c_src[(i, k)] * x[(i, k)] for i in sources for k in stations) + \
                gp.quicksum(c_dst[(k, j)] * z[(k, j)] for k in stations for j in demands) + \
                gp.quicksum(f[k] * y[k] for k in stations)

    m.setObjective(objective, GRB.MINIMIZE)

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
        "y_2": y[2]
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, "UNKNOWN")

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    result = {
        "status": status,
        "objective": float(model.ObjVal),
        "solution": solution
    }
    return result