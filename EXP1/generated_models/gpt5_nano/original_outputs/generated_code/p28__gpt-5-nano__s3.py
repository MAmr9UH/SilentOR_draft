import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    warehouses = data["warehouses"]
    ports = data["ports"]

    supply = data["supply"]
    demand = data["demand"]
    distance_km = data["distance_km"]
    capacity = data["truck_capacity_containers"]
    cost_per_km = data["cost_per_km_per_truck"]

    # Decision variables
    x = {}  # containers shipped
    t = {}  # truck trips

    # Create x variables
    for w in warehouses:
        for p in ports:
            key = f"x_{w}_{p}"
            var = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
            x[key] = var

    # Create t variables
    for w in warehouses:
        for p in ports:
            key = f"t_{w}_{p}"
            var = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
            t[key] = var

    model.update()

    # Supply constraints: sum of shipments from each warehouse <= supply
    for w in warehouses:
        expr = gp.quicksum(x[f"x_{w}_{p}"] for p in ports)
        model.addConstr(expr <= supply[w], name=f"Supply_{w}")

    # Demand constraints: sum of shipments to each port == demand
    for p in ports:
        expr = gp.quicksum(x[f"x_{w}_{p}"] for w in warehouses)
        model.addConstr(expr == demand[p], name=f"Demand_{p}")

    # Capacity constraints: x_w_p <= capacity * t_w_p
    for w in warehouses:
        for p in ports:
            model.addConstr(x[f"x_{w}_{p}"] <= capacity * t[f"t_{w}_{p}"])

    # Objective: minimize transportation cost (distance * cost per km * containers)
    objective = gp.quicksum(cost_per_km * distance_km[w][p] * x[f"x_{w}_{p}"] for w in warehouses for p in ports)
    model.setObjective(objective, GRB.MINIMIZE)

    # Prepare variables dictionary to return
    variables = dict(x)
    variables.update(t)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values for all variables
    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }