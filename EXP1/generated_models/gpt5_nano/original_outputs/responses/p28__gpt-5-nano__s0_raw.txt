import gurobipy as gp
from gurobipy import GRB

# Build the optimization model but do not solve it here
def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    distance = data["distance_km"]
    cap = data["truck_capacity_containers"]
    cost = data["cost_per_km_per_truck"]

    model = gp.Model()

    # Decision variables
    x = {}  # containers shipped from warehouse i to port j
    t = {}  # truck trips from warehouse i to port j
    for w in warehouses:
        for p in ports:
            x[(w, p)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{w}_{p}")
            t[(w, p)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"t_{w}_{p}")

    model.update()

    # Supply constraints: total shipped from each warehouse cannot exceed its supply
    for w in warehouses:
        model.addConstr(gp.quicksum(x[(w, p)] for p in ports) <= supply[w], name=f"Supply_{w}")

    # Demand constraints: each port must receive exactly its demand
    for p in ports:
        model.addConstr(gp.quicksum(x[(w, p)] for w in warehouses) == demand[p], name=f"Demand_{p}")

    # Capacity constraints: x[i,j] <= 2 * t[i,j] (each trip can carry up to 2 containers)
    for w in warehouses:
        for p in ports:
            model.addConstr(x[(w, p)] <= cap * t[(w, p)], name=f"Cap_{w}_{p}")

    # Objective: minimize total cost = sum(cost * distance * x[i,j])
    obj = gp.quicksum(cost * distance[w][p] * x[(w, p)] for w in warehouses for p in ports)
    model.setObjective(obj, GRB.MINIMIZE)

    # Flattened dictionary of all variables to return
    variables = {}
    for w in warehouses:
        for p in ports:
            variables[f"x_{w}_{p}"] = x[(w, p)]
    for w in warehouses:
        for p in ports:
            variables[f"t_{w}_{p}"] = t[(w, p)]

    return model, variables

# Solve the model and return the prescribed solution format
def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    # Build solution dictionary with all variable values
    solution = {}
    for key, var in variables.items():
        val = var.X
        # Cast to int if essentially integral
        if abs(val - round(val)) < 1e-6:
            solution[key] = int(round(val))
        else:
            solution[key] = float(val)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }