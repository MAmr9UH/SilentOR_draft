import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    warehouses = data["warehouses"]
    ports = data["ports"]

    model = gp.Model()

    x_vars = {}
    t_vars = {}
    variables = {}

    for w in warehouses:
        for p in ports:
            keyx = f"x_{w}_{p}"
            vx = model.addVar(vtype=GRB.INTEGER, lb=0, name=keyx)
            x_vars[(w, p)] = vx
            variables[keyx] = vx

            keyt = f"t_{w}_{p}"
            vt = model.addVar(vtype=GRB.INTEGER, lb=0, name=keyt)
            t_vars[(w, p)] = vt
            variables[keyt] = vt

    # Supply constraints: sum_p x_{w,p} <= supply[w]
    for w in warehouses:
        model.addConstr(gp.quicksum(x_vars[(w, p)] for p in ports) <= data["supply"][w], name=f"Supply_{w}")

    # Demand constraints: sum_w x_{w,p} == demand[p]
    for p in ports:
        model.addConstr(gp.quicksum(x_vars[(w, p)] for w in warehouses) == data["demand"][p], name=f"Demand_{p}")

    # Linking constraints: x_{w,p} <= 2 * t_{w,p}
    for w in warehouses:
        for p in ports:
            model.addConstr(x_vars[(w, p)] <= 2 * t_vars[(w, p)], name=f"Link_{w}_{p}")

    # Objective: minimize total cost = sum_over_w_p (cost_per_km * distance * x_{w,p})
    dist = data["distance_km"]
    ckm = data["cost_per_km_per_truck"]
    objective = gp.quicksum(ckm * dist[w][p] * x_vars[(w, p)] for w in warehouses for p in ports)
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    objective_value = float(model.ObjVal)

    solution_values = {}
    for key, var in variables.items():
        solution_values[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution_values
    }