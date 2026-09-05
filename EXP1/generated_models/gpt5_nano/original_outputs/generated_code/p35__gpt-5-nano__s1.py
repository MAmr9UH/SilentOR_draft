from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    m = Model()
    # Decision variables
    x_11 = m.addVar(lb=0, name="x_1_1")
    x_12 = m.addVar(lb=0, name="x_1_2")
    x_21 = m.addVar(lb=0, name="x_2_1")
    x_22 = m.addVar(lb=0, name="x_2_2")

    z_11 = m.addVar(lb=0, name="z_1_1")
    z_12 = m.addVar(lb=0, name="z_1_2")
    z_21 = m.addVar(lb=0, name="z_2_1")
    z_22 = m.addVar(lb=0, name="z_2_2")

    y_1 = m.addVar(vtype=GRB.BINARY, name="y_1")
    y_2 = m.addVar(vtype=GRB.BINARY, name="y_2")

    m.update()

    xi = {(1,1): x_11, (1,2): x_12, (2,1): x_21, (2,2): x_22}
    zi = {(1,1): z_11, (1,2): z_12, (2,1): z_21, (2,2): z_22}
    y = {1: y_1, 2: y_2}

    # Data extraction
    supply = data["supply"]
    demand = data["demand"]
    capacity = data["station_capacity"]
    fixed = data["fixed_cost"]
    cost_src = data["cost_source_station"]
    cost_dest = data["cost_station_demand"]

    # Supply constraints: sum_k x_{i,k} <= a_i
    for i in [1, 2]:
        m.addConstr(quicksum(xi[(i, k)] for k in [1, 2]) <= float(supply[str(i)]))

    # Demand constraints: sum_k z_{k,j} == b_j
    for j in [1, 2]:
        m.addConstr(quicksum(zi[(k, j)] for k in [1, 2]) == float(demand[str(j)]))

    # Flow conservation at stations: sum_i x_{i,k} == sum_j z_{k,j}
    for k in [1, 2]:
        m.addConstr(quicksum(xi[(i, k)] for i in [1, 2]) == quicksum(zi[(k, j)] for j in [1, 2]))
        # Capacity with fixed cost if used
        m.addConstr(quicksum(xi[(i, k)] for i in [1, 2]) <= float(capacity[str(k)]) * y[k])

    # Objective: transportation costs + fixed costs
    obj = quicksum(float(cost_src[f"{i},{k}"]) * xi[(i, k)] for i in [1, 2] for k in [1, 2])
    obj += quicksum(float(cost_dest[f"{k},{j}"]) * zi[(k, j)] for k in [1, 2] for j in [1, 2])
    obj += quicksum(float(fixed[str(k)]) * y[k] for k in [1, 2])

    m.setObjective(obj, GRB.MINIMIZE)

    variables = {
        "x_1_1": x_11,
        "x_1_2": x_12,
        "x_2_1": x_21,
        "x_2_2": x_22,
        "z_1_1": z_11,
        "z_1_2": z_12,
        "z_2_1": z_21,
        "z_2_2": z_22,
        "y_1": y_1,
        "y_2": y_2
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
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    solution = {k: float(variables[k].X) for k in [
        "x_1_1", "x_1_2", "x_2_1", "x_2_2",
        "z_1_1", "z_1_2", "z_2_1", "z_2_2",
        "y_1", "y_2"
    ]}

    result = {
        "status": status,
        "objective": float(model.ObjVal),
        "solution": solution
    }
    return result