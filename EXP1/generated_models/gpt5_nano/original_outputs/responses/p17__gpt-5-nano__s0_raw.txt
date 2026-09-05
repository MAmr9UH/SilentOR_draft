from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    """
    Build and return the Gurobi model and a flat dictionary of all decision variables.
    """
    centers = data.get("centers", [])
    stores = data.get("stores", [])
    
    model = Model()
    model.Params.LogToConsole = 0

    # Decision variables
    y = {}
    for idx in range(1, len(centers) + 1):
        name = f"y_c{idx}"
        y[name] = model.addVar(vtype=GRB.BINARY, name=name)

    f = {}
    for c_idx in range(1, len(centers) + 1):
        for s_idx in range(1, len(stores) + 1):
            name = f"f_c{c_idx}_s{s_idx}"
            f[name] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=name)

    model.update()

    # Objective: minimize opening costs plus transportation costs
    obj = quicksum(data["fixed_opening_cost"][f"c{ci}"] * y[f"y_c{ci}"] for ci in range(1, len(centers) + 1))
    for ci in range(1, len(centers) + 1):
        for si in range(1, len(stores) + 1):
            obj += data["transport_cost"][f"c{ci}"][f"s{si}"] * f[f"f_c{ci}_s{si}"]
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints: meet demand at each store
    for si in range(1, len(stores) + 1):
        demand = data["demand"][f"s{si}"]
        model.addConstr(quicksum(f[f"f_c{ci}_s{si}"] for ci in range(1, len(centers) + 1)) >= demand)

    # Constraints: center capacities limited by whether the center is opened
    for ci in range(1, len(centers) + 1):
        cap = data["capacity"][f"c{ci}"]
        model.addConstr(quicksum(f[f"f_c{ci}_s{si}"] for si in range(1, len(stores) + 1)) <= cap * y[f"y_c{ci}"])

    # Return model and a flat dictionary of all variables
    variables = {}
    variables.update(f)
    variables.update(y)

    return model, variables


def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    solution = {key: float(var.X) for key, var in variables.items()}

    return {
        "status": status,
        "objective": float(model.ObjVal),
        "solution": solution
    }