import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    # Determine problem sizes from data
    m = len(data.get("sources", []))
    p = len(data.get("stations", []))
    n = len(data.get("demands", []))

    # Supplies and demands
    supply = {i: float(data["supply"][str(i)]) for i in range(1, m + 1)}
    demand = {j: float(data["demand"][str(j)]) for j in range(1, n + 1)}
    q = {k: float(data["station_capacity"][str(k)]) for k in range(1, p + 1)}
    f = {k: float(data["fixed_cost"][str(k)]) for k in range(1, p + 1)}

    # Costs
    c = {}
    for i in range(1, m + 1):
        for k in range(1, p + 1):
            c[(i, k)] = float(data["cost_source_station"][f"{i},{k}"])
    cp = {}
    for k in range(1, p + 1):
        for j in range(1, n + 1):
            cp[(k, j)] = float(data["cost_station_demand"][f"{k},{j}"])

    model = gp.Model()

    # Decision variables
    x = {}
    for i in range(1, m + 1):
        for k in range(1, p + 1):
            x[(i, k)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{i}_{k}")

    z = {}
    for k in range(1, p + 1):
        for j in range(1, n + 1):
            z[(k, j)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"z_{k}_{j}")

    y = {}
    for k in range(1, p + 1):
        y[k] = model.addVar(vtype=GRB.BINARY, name=f"y_{k}")

    model.update()

    # Objective
    obj = gp.quicksum(c[(i, k)] * x[(i, k)] for i in range(1, m + 1) for k in range(1, p + 1)) \
          + gp.quicksum(cp[(k, j)] * z[(k, j)] for k in range(1, p + 1) for j in range(1, n + 1)) \
          + gp.quicksum(f[k] * y[k] for k in range(1, p + 1))

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Supply constraints
    for i in range(1, m + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for k in range(1, p + 1)) <= supply[i],
                        name=f"supply_{i}")

    # Flow conservation at marshaling stations
    for k in range(1, p + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for i in range(1, m + 1)) == gp.quicksum(z[(k, j)] for j in range(1, n + 1)),
                        name=f"flow_{k}")

    # Capacity constraints with fixed costs
    for k in range(1, p + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for i in range(1, m + 1)) <= q[k] * y[k],
                        name=f"cap_{k}")

    # Demand satisfaction
    for j in range(1, n + 1):
        model.addConstr(gp.quicksum(z[(k, j)] for k in range(1, p + 1)) == demand[j],
                        name=f"demand_{j}")

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
    model.update()

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

    objective = float(model.ObjVal)

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