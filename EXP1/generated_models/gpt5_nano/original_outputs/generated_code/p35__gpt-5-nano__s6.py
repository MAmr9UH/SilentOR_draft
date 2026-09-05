import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # problem dimensions
    m = len(data["sources"])
    p = len(data["stations"])
    n = len(data["demands"])

    # helper indices (1-based as in data)
    # Variables
    x = {}
    for i in range(1, m + 1):
        for k in range(1, p + 1):
            x[(i, k)] = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name=f"x_{i}_{k}")

    z = {}
    for k in range(1, p + 1):
        for j in range(1, n + 1):
            z[(k, j)] = model.addVar(lb=0.0, ub=GRB.INFINITY, vtype=GRB.CONTINUOUS, name=f"z_{k}_{j}")

    y = {}
    for k in range(1, p + 1):
        y[k] = model.addVar(vtype=GRB.BINARY, name=f"y_{k}")

    model.update()

    # Objective
    obj = gp.quicksum(data["cost_source_station"][f"{i},{k}"] * x[(i, k)]
                      for i in range(1, m + 1) for k in range(1, p + 1)) \
          + gp.quicksum(data["cost_station_demand"][f"{k},{j}"] * z[(k, j)]
                      for k in range(1, p + 1) for j in range(1, n + 1)) \
          + gp.quicksum(data["fixed_cost"][f"{k}"] * y[k] for k in range(1, p + 1))
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Supply constraints
    for i in range(1, m + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for k in range(1, p + 1)) <= data["supply"][str(i)])

    # Demand constraints
    for j in range(1, n + 1):
        model.addConstr(gp.quicksum(z[(k, j)] for k in range(1, p + 1)) == data["demand"][str(j)])

    # Flow balance at each station
    for k in range(1, p + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for i in range(1, m + 1)) == gp.quicksum(z[(k, j)] for j in range(1, n + 1)))

    # Capacity with fixed charges
    for k in range(1, p + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for i in range(1, m + 1)) <= data["station_capacity"][str(k)] * y[k])
        model.addConstr(gp.quicksum(z[(k, j)] for j in range(1, n + 1)) <= data["station_capacity"][str(k)] * y[k])

    # Return variables to user
    variables = {
        "x_1_1": x[(1, 1)], "x_1_2": x[(1, 2)],
        "x_2_1": x[(2, 1)], "x_2_2": x[(2, 2)],
        "z_1_1": z[(1, 1)], "z_1_2": z[(1, 2)],
        "z_2_1": z[(2, 1)], "z_2_2": z[(2, 2)],
        "y_1": y[1], "y_2": y[2]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(st)

    # Objective value
    model.update()
    obj_val = float(model.ObjVal)

    # Solution values
    sol = {
        "x_1_1": float(variables["x_1_1"].X),
        "x_1_2": float(variables["x_1_2"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_2": float(variables["x_2_2"].X),
        "z_1_1": float(variables["z_1_1"].X),
        "z_1_2": float(variables["z_1_2"].X),
        "z_2_1": float(variables["z_2_1"].X),
        "z_2_2": float(variables["z_2_2"].X),
        "y_1": float(variables["y_1"].X),
        "y_2": float(variables["y_2"].X)
    }

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": sol
    }