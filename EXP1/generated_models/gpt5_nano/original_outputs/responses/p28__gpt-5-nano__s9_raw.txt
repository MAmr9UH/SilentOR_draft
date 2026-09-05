import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model("ContainerTransport")

    warehouses = data["warehouses"]
    ports = data["ports"]

    supply = data["supply"]
    demand = data["demand"]
    distance_km = data["distance_km"]
    cost_per_km_per_truck = data["cost_per_km_per_truck"]

    truck_capacity_containers = data["truck_capacity_containers"]

    variables = {}

    # Decision variables: x_i_j (containers shipped) and t_i_j (truck trips)
    for w in warehouses:
        for p in ports:
            name_x = f"x_{w}_{p}"
            v = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=name_x)
            variables[name_x] = v

    for w in warehouses:
        for p in ports:
            name_t = f"t_{w}_{p}"
            v = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=name_t)
            variables[name_t] = v

    # Objective: minimize total cost
    objective = gp.quicksum(cost_per_km_per_truck * distance_km[w][p] * variables[f"t_{w}_{p}"]
                            for w in warehouses for p in ports)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    # Supply constraints: sum_j x_i_j <= supply_i
    for w in warehouses:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{p}"] for p in ports) <= supply[w],
                        name=f"Supply_{w}")

    # Demand constraints: sum_i x_i_j == demand_j
    for p in ports:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{p}"] for w in warehouses) == demand[p],
                        name=f"Demand_{p}")

    # Truck capacity constraints: x_i_j <= 2 * t_i_j
    for w in warehouses:
        for p in ports:
            model.addConstr(variables[f"x_{w}_{p}"] <= 2 * variables[f"t_{w}_{p}"],
                            name=f"TruckCap_{w}_{p}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status as string
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

    objective_value = float(model.ObjVal)

    # Prepare solution dict in required order
    warehouses = data["warehouses"]
    ports = data["ports"]

    solution = {}
    # x variables in the order: Verona, Perugia, Rome, Pescara, Taranto, Lamezia
    for w in warehouses:
        for p in ports:
            solution[f"x_{w}_{p}"] = float(variables[f"x_{w}_{p}"].X)

    # t variables in the same order
    for w in warehouses:
        for p in ports:
            solution[f"t_{w}_{p}"] = float(variables[f"t_{w}_{p}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }