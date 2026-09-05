import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    distance_km = data["distance_km"]
    cost_per_km_per_truck = data["cost_per_km_per_truck"]
    truck_capacity = data["truck_capacity_containers"]

    model = gp.Model()

    # Create decision variables
    variables = {}

    for w in warehouses:
        for p in ports:
            x_key = f"x_{w}_{p}"
            t_key = f"t_{w}_{p}"
            x_var = model.addVar(vtype=GRB.INTEGER, lb=0, name=x_key)
            t_var = model.addVar(vtype=GRB.INTEGER, lb=0, name=t_key)
            variables[x_key] = x_var
            variables[t_key] = t_var

    model.update()

    # Supply constraints: sum_p x_wp <= supply_w
    for w in warehouses:
        model.addConstr(quicksum(variables[f"x_{w}_{p}"] for p in ports) <= supply[w],
                        name=f"Supply_{w}")

    # Demand constraints: sum_w x_wp == demand_p
    for p in ports:
        model.addConstr(quicksum(variables[f"x_{w}_{p}"] for w in warehouses) == demand[p],
                        name=f"Demand_{p}")

    # Truck capacity constraints: x_wp <= capacity * t_wp
    for w in warehouses:
        for p in ports:
            model.addConstr(variables[f"x_{w}_{p}"] <= truck_capacity * variables[f"t_{w}_{p}"],
                            name=f"TruckCap_{w}_{p}")

    # Objective: Minimize total cost = sum(cost_per_km * distance * t_wp)
    model.setObjective(
        quicksum(cost_per_km_per_truck * distance_km[w][p] * variables[f"t_{w}_{p}"]
                 for w in warehouses for p in ports),
        GRB.MINIMIZE
    )

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Read status and objective
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal)

    # Ensure model values are up-to-date
    model.update()

    # Build solution dictionary with all required keys
    solution = {}
    warehouses = data["warehouses"]
    ports = data["ports"]

    # x variables
    for w in warehouses:
        for p in ports:
            key = f"x_{w}_{p}"
            solution[key] = int(variables[key].X)

    # t variables
    for w in warehouses:
        for p in ports:
            key = f"t_{w}_{p}"
            solution[key] = int(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }