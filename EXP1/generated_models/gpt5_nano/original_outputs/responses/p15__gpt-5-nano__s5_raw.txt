import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    cap = {c: data["capacity"][c] for c in centers}
    opening_cost = {c: data["fixed_opening_cost"][c] for c in centers}
    transport = data["transport_cost"]
    demand = data["demand"]

    # Variables
    y = {}
    f = {c: {} for c in centers}
    variables = {}

    # Opening decisions
    for c in centers:
        v = m.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y[c] = v
        variables[f"y_{c}"] = v

    # Transportation flows
    for c in centers:
        for s in stores:
            v = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
            f[c][s] = v
            variables[f"f_{c}_{s}"] = v

    m.update()

    # Objective: minimize opening costs + transport costs
    obj = gp.quicksum(opening_cost[c] * y[c] for c in centers) \
          + gp.quicksum(transport[c][s] * f[c][s] for c in centers for s in stores)
    m.setObjective(obj, GRB.MINIMIZE)

    total_demand = sum(demand.values())

    # Demand satisfaction
    for s in stores:
        m.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints
    for c in centers:
        m.addConstr(gp.quicksum(f[c][s] for s in stores) <= cap[c] * y[c], name=f"cap_{c}")

    # Linking constraints: if center not opened, shipments must be zero
    for c in centers:
        for s in stores:
            m.addConstr(f[c][s] <= total_demand * y[c], name=f"link_{c}_{s}")

    m.update()

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal)

    solution = {}

    # y variables in order y_c1 .. y_c5
    for i in range(1, 6):
        key = f"y_c{i}"
        solution[key] = float(variables[key].X)

    # f variables in order f_c1_s1 .. f_c5_s7
    for i in range(1, 6):
        c = f"c{i}"
        for j in range(1, 8):
            s = f"s{j}"
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }