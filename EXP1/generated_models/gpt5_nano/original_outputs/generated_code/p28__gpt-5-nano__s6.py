import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    warehouses = list(data["warehouses"])
    ports = list(data["ports"])

    model = gp.Model()

    # Decision variables
    x = {}
    t = {}

    for w in warehouses:
        for p in ports:
            keyx = f"x_{w}_{p}"
            x[(w, p)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=keyx)

    for w in warehouses:
        for p in ports:
            keyt = f"t_{w}_{p}"
            t[(w, p)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=keyt)

    model.update()

    # Objective: minimize total transportation cost
    dist = data["distance_km"]
    cost_per_km = data["cost_per_km_per_truck"]
    obj = gp.quicksum(cost_per_km * dist[w][p] * t[(w, p)] for w in warehouses for p in ports)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Supply constraints: sum_p x_wp <= supply_w
    supply = data["supply"]
    for w in warehouses:
        model.addConstr(gp.quicksum(x[(w, p)] for p in ports) <= supply[w])

    # Demand constraints: sum_w x_wp == demand_p
    demand = data["demand"]
    for p in ports:
        model.addConstr(gp.quicksum(x[(w, p)] for w in warehouses) == demand[p])

    # Capacity constraints: x_wp <= capacity * t_wp
    cap = data["truck_capacity_containers"]
    for w in warehouses:
        for p in ports:
            model.addConstr(x[(w, p)] <= cap * t[(w, p)])

    # Prepare variables dictionary to return
    variables = {}
    for w in warehouses:
        for p in ports:
            keyx = f"x_{w}_{p}"
            variables[keyx] = x[(w, p)]
    for w in warehouses:
        for p in ports:
            keyt = f"t_{w}_{p}"
            variables[keyt] = t[(w, p)]

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
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    else:
        status = str(st)

    objective = float(model.ObjVal)

    solution = {}
    warehouses = list(data["warehouses"])
    ports = list(data["ports"])
    for w in warehouses:
        for p in ports:
            keyx = f"x_{w}_{p}"
            solution[keyx] = float(variables[keyx].X)

    for w in warehouses:
        for p in ports:
            keyt = f"t_{w}_{p}"
            solution[keyt] = float(variables[keyt].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }