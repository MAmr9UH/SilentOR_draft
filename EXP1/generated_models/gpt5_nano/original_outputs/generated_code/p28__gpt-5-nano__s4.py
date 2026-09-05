from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    distance = data["distance_km"]
    cap = data.get("truck_capacity_containers", 2)
    cost_per_km = data.get("cost_per_km_per_truck", 30)

    model = Model()

    # Decision variables
    x = {}
    t = {}
    for w in warehouses:
        for p in ports:
            x[(w, p)] = model.addVar(vtype=GRB.INTEGER, name=f"x_{w}_{p}", lb=0)
            t[(w, p)] = model.addVar(vtype=GRB.INTEGER, name=f"t_{w}_{p}", lb=0)

    model.update()

    # Objective: minimize total transport cost
    model.setObjective(
        quicksum(distance[w][p] * x[(w, p)] for w in warehouses for p in ports) * cost_per_km,
        GRB.MINIMIZE
    )

    # Constraints
    # Supply: do not ship more than available at each warehouse
    for w in warehouses:
        model.addConstr(quicksum(x[(w, p)] for p in ports) <= supply[w], name=f"Supply_{w}")

    # Demand: meet all port demands
    for p in ports:
        model.addConstr(quicksum(x[(w, p)] for w in warehouses) == demand[p], name=f"Demand_{p}")

    # Truck capacity: x <= cap * t (t is integer, number of trips)
    for w in warehouses:
        for p in ports:
            model.addConstr(x[(w, p)] <= cap * t[(w, p)], name=f"Cap_{w}_{p}")

    model.update()

    # Expose all variables in a flat dictionary with exact keys
    variables = {}
    for w in warehouses:
        for p in ports:
            variables[f"x_{w}_{p}"] = x[(w, p)]
    for w in warehouses:
        for p in ports:
            variables[f"t_{w}_{p}"] = t[(w, p)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(st)

    objective = float(model.ObjVal) if model.ObjVal is not None else 0.0

    solution = {}
    model.update()
    for key in variables:
        solution[key] = int(round(variables[key].X))

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }