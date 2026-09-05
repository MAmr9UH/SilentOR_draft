import gurobipy as gp
from gurobipy import GRB

def _status_to_string(status_int: int) -> str:
    mapping = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    return mapping.get(status_int, "UNKNOWN")

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parse data
    supply = {int(k): v for k, v in data["supply"].items()}
    demand = {int(k): v for k, v in data["demand"].items()}
    station_cap = {int(k): v for k, v in data["station_capacity"].items()}
    fixed_cost = {int(k): v for k, v in data["fixed_cost"].items()}
    c_ss = {}
    for key, val in data["cost_source_station"].items():
        i, k = map(int, key.split(","))
        c_ss[(i, k)] = val
    c_sd = {}
    for key, val in data["cost_station_demand"].items():
        k, j = map(int, key.split(","))
        c_sd[(k, j)] = val

    m = len(supply)
    p = len(station_cap)
    n = len(demand)

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

    # Objective: Minimize transportation cost plus fixed charges
    obj = gp.quicksum(c_ss[(i, k)] * x[(i, k)] for i in range(1, m + 1) for k in range(1, p + 1)) \
        + gp.quicksum(c_sd[(k, j)] * z[(k, j)] for k in range(1, p + 1) for j in range(1, n + 1)) \
        + gp.quicksum(fixed_cost[k] * y[k] for k in range(1, p + 1))

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # Supply constraints
    for i in range(1, m + 1):
        model.addConstr(gp.quicksum(x[(i, k)] for k in range(1, p + 1)) <= supply[i], name=f"Supply_{i}")

    # Demand constraints
    for j in range(1, n + 1):
        model.addConstr(gp.quicksum(z[(k, j)] for k in range(1, p + 1)) == demand[j], name=f"Demand_{j}")

    # Flow balance at stations and capacity with fixed charge
    for k in range(1, p + 1):
        inflow = gp.quicksum(x[(i, k)] for i in range(1, m + 1))
        outflow = gp.quicksum(z[(k, j)] for j in range(1, n + 1))
        model.addConstr(inflow == outflow, name=f"Flow_{k}")

        model.addConstr(inflow <= station_cap[k] * y[k], name=f"CapIn_{k}")
        model.addConstr(outflow <= station_cap[k] * y[k], name=f"CapOut_{k}")

    # Return model and variable dictionary with exact keys
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

    status_str = _status_to_string(model.Status)
    objective = float(model.ObjVal)

    # Read solution values
    model.update()
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
        "objective": objective,
        "solution": solution
    }