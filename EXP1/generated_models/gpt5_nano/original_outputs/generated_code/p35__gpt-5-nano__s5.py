import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Decision variables
    x = {}
    for i in (1, 2):
        for k in (1, 2):
            x[(i, k)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{i}_{k}")

    z = {}
    for k in (1, 2):
        for j in (1, 2):
            z[(k, j)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"z_{k}_{j}")

    y = {}
    for k in (1, 2):
        y[k] = model.addVar(vtype=GRB.BINARY, name=f"y_{k}")

    model.update()

    # Objective: minimize total cost
    obj = gp.quicksum(data["cost_source_station"][f"{i},{k}"] * x[(i, k)]
                      for i in (1, 2) for k in (1, 2)) \
          + gp.quicksum(data["cost_station_demand"][f"{k},{j}"] * z[(k, j)]
                        for k in (1, 2) for j in (1, 2)) \
          + gp.quicksum(data["fixed_cost"][str(k)] * y[k] for k in (1, 2))
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for j in (1, 2):
        model.addConstr(gp.quicksum(z[(k, j)] for k in (1, 2)) == data["demand"][str(j)],
                        name=f"Demand_{j}")

    # Supply limitations
    for i in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for k in (1, 2)) <= data["supply"][str(i)],
                        name=f"Supply_{i}")

    # Flow conservation at stations and capacity with fixed cost
    for k in (1, 2):
        model.addConstr(gp.quicksum(x[(i, k)] for i in (1, 2)) - gp.quicksum(z[(k, j)] for j in (1, 2)) == 0,
                        name=f"Flow_eq_{k}")
        model.addConstr(gp.quicksum(x[(i, k)] for i in (1, 2)) <= data["station_capacity"][str(k)] * y[k],
                        name=f"Cap_y_{k}")

    model.update()

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

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CUTOFF: "CUTOFF",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    objective_value = model.ObjVal

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
        "y_2": float(variables["y_2"].X)
    }

    return {
        "status": status_str,
        "objective": float(objective_value),
        "solution": solution
    }