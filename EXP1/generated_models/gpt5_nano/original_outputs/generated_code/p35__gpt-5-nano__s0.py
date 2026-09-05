import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parse data
    supply = {1: data["supply"]["1"], 2: data["supply"]["2"]}
    demand = {1: data["demand"]["1"], 2: data["demand"]["2"]}
    q = {1: data["station_capacity"]["1"], 2: data["station_capacity"]["2"]}
    f = {1: data["fixed_cost"]["1"], 2: data["fixed_cost"]["2"]}

    c_source = {
        (1, 1): data["cost_source_station"]["1,1"],
        (1, 2): data["cost_source_station"]["1,2"],
        (2, 1): data["cost_source_station"]["2,1"],
        (2, 2): data["cost_source_station"]["2,2"],
    }
    c_station = {
        (1, 1): data["cost_station_demand"]["1,1"],
        (1, 2): data["cost_station_demand"]["1,2"],
        (2, 1): data["cost_station_demand"]["2,1"],
        (2, 2): data["cost_station_demand"]["2,2"],
    }

    variables = {}

    # Decision variables
    x = {}
    for i in (1, 2):
        for k in (1, 2):
            var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{i}_{k}")
            x[(i, k)] = var
            variables[f"x_{i}_{k}"] = var

    z = {}
    for k in (1, 2):
        for j in (1, 2):
            var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"z_{k}_{j}")
            z[(k, j)] = var
            variables[f"z_{k}_{j}"] = var

    y = {}
    for k in (1, 2):
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{k}")
        y[k] = var
        variables[f"y_{k}"] = var

    model.update()

    # Objective
    obj = gp.quicksum(c_source[(i, k)] * x[(i, k)] for i in (1, 2) for k in (1, 2)) \
        + gp.quicksum(c_station[(k, j)] * z[(k, j)] for k in (1, 2) for j in (1, 2)) \
        + gp.quicksum(f[k] * y[k] for k in (1, 2))

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # Supply constraints
    for i in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for k in (1, 2)) <= supply[i], name=f"supply_{i}")

    # Demand constraints
    for j in (1, 2):
        model.addConstr(gp.quicksum(z[(k, j)] for k in (1, 2)) == demand[j], name=f"demand_{j}")

    # Flow conservation at marshaling stations
    for k in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for i in (1, 2)) == gp.quicksum(z[(k, j)] for j in (1, 2)), name=f"flow_{k}")

    # Capacity constraints for each station
    for k in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for i in (1, 2)) <= q[k], name=f"cap_in_{k}")
        model.addConstr(gp.quicksum(z[(k, j)] for j in (1, 2)) <= q[k], name=f"cap_out_{k}")

    # Linking to fixed costs: if a station is used, at least some flow must pass
    for k in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for i in (1, 2)) <= q[k] * y[k], name=f"link_in_{k}")
        model.addConstr(gp.quicksum(z[(k, j)] for j in (1, 2)) <= q[k] * y[k], name=f"link_out_{k}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    obj_val = float(model.ObjVal)

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
        "objective": obj_val,
        "solution": solution
    }