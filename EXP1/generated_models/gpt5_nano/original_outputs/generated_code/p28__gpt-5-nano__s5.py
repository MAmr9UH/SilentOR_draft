import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]
    supply = data["supply"]
    demand = data["demand"]
    distance_km = data["distance_km"]
    cost_per_km_per_truck = data["cost_per_km_per_truck"]

    model = gp.Model("ContainerMovement")

    # Dictionaries to hold variables
    variables = {}

    # Decision variables: x_i_j (containers moved)
    x = {}
    for w in warehouses:
        for p in ports:
            name = f"x_{w}_{p}"
            v = model.addVar(vtype=GRB.INTEGER, lb=0, name=name)
            x[(w, p)] = v
            variables[name] = v

    # Transportation/trip variables: t_i_j (truck trips)
    t = {}
    for w in warehouses:
        for p in ports:
            name = f"t_{w}_{p}"
            v = model.addVar(vtype=GRB.INTEGER, lb=0, name=name)
            t[(w, p)] = v
            variables[name] = v

    model.update()

    # Objective: minimize cost = sum distance * x * cost_per_km_per_truck
    obj_expr = gp.quicksum(distance_km[w][p] * x[(w, p)] for w in warehouses for p in ports)
    model.setObjective(cost_per_km_per_truck * obj_expr, GRB.MINIMIZE)

    # Constraints
    # Supply constraints: sum_j x_i_j <= supply_i
    for w in warehouses:
        model.addConstr(gp.quicksum(x[(w, p)] for p in ports) <= supply[w], name=f"Supply_{w}")

    # Demand constraints: sum_i x_i_j == demand_j
    for p in ports:
        model.addConstr(gp.quicksum(x[(w, p)] for w in warehouses) == demand[p], name=f"Demand_{p}")

    # Capacity constraints: 2 * t_i_j >= x_i_j for all i,j
    for w in warehouses:
        for p in ports:
            model.addConstr(2 * t[(w, p)] >= x[(w, p)], name=f"Cap_{w}_{p}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    else:
        status = str(st)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    for key, var in variables.items():
        val = var.X
        if isinstance(val, float) and abs(val - round(val)) < 1e-6:
            val = int(round(val))
        solution[key] = val

    return {
        "status": status,
        "objective": objective_value,
        "solution": solution
    }