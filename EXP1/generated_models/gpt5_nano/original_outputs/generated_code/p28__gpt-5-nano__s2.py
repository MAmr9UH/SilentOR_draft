import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    dist = data["distance_km"]
    cost_per_km = data["cost_per_km_per_truck"]

    model = gp.Model("shipments")

    # Decision variables
    x = {}
    t = {}
    for w in warehouses:
        for p in ports:
            x[(w, p)] = model.addVar(lb=0, vtype=GRB.INTEGER, name=f"x_{w}_{p}")
            t[(w, p)] = model.addVar(lb=0, vtype=GRB.INTEGER, name=f"t_{w}_{p}")

    # Objective: minimize total transport cost (per container)
    objective = gp.quicksum(cost_per_km * dist[w][p] * x[(w, p)] for w in warehouses for p in ports)
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints
    # 1) Supply constraints: shipped from each warehouse cannot exceed its supply
    for w in warehouses:
        model.addConstr(gp.quicksum(x[(w, p)] for p in ports) <= supply[w], name=f"Supply_{w}")

    # 2) Demand constraints: meet demand at each port (exactly)
    for p in ports:
        model.addConstr(gp.quicksum(x[(w, p)] for w in warehouses) >= demand[p], name=f"Demand_{p}")

    # 3) Capacity per route: x[w,p] <= 2 * t[w,p]
    for w in warehouses:
        for p in ports:
            model.addConstr(x[(w, p)] <= 2 * t[(w, p)], name=f"Cap_{w}_{p}")

    model.update()

    # Build the variables dictionary with exact keys
    variables = {}
    for w in warehouses:
        for p in ports:
            key = f"x_{w}_{p}"
            variables[key] = x[(w, p)]
    for w in warehouses:
        for p in ports:
            key = f"t_{w}_{p}"
            variables[key] = t[(w, p)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    # Objective value
    objective_value = float(model.ObjVal)

    # Solution dictionary
    solution = {}
    model.update()
    for key, var in variables.items():
        val = var.X
        # Cast to int if value is essentially integer
        if abs(val - round(val)) < 1e-6:
            val = int(round(val))
        else:
            val = float(val)
        solution[key] = val

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }