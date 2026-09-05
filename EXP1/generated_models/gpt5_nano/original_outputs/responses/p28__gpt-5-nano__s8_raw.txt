import gurobipy as gp

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    distance = data["distance_km"]
    cap = data["truck_capacity_containers"]
    cost_per_km = data["cost_per_km_per_truck"]

    model = gp.Model("ContainerTransport")

    # Variables: x_w_p (containers shipped) and t_w_p (truck trips)
    variables = {}

    # Create x variables
    for w in warehouses:
        for p in ports:
            key = f"x_{w}_{p}"
            v = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=key)
            variables[key] = v

    # Supply constraints: sum_j x_wj <= supply_w
    for w in warehouses:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{p}"] for p in ports) <= supply[w],
                        name=f"Supply_{w}")

    # Demand constraints: sum_w x_wj == demand_j
    for p in ports:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{p}"] for w in warehouses) == demand[p],
                        name=f"Demand_{p}")

    # Create t variables
    for w in warehouses:
        for p in ports:
            key = f"t_{w}_{p}"
            v = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=key)
            variables[key] = v

    # Truck capacity constraints: cap * t_wj >= x_wj
    for w in warehouses:
        for p in ports:
            model.addConstr(cap * variables[f"t_{w}_{p}"] >= variables[f"x_{w}_{p}"],
                            name=f"TruckCap_{w}_{p}")

    # Objective: minimize cost = sum distance * cost_per_km * t_wj
    obj = gp.quicksum(distance[w][p] * cost_per_km * variables[f"x_{w}_{p}"]
                      for w in warehouses for p in ports)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary in the required order
    solution = {}
    for w in data["warehouses"]:
        for p in data["ports"]:
            key = f"x_{w}_{p}"
            solution[key] = int(variables[key].X)

    for w in data["warehouses"]:
        for p in data["ports"]:
            key = f"t_{w}_{p}"
            solution[key] = int(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }