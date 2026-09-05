import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    m = gp.Model("SC_Location_Allocation")

    # Decision variables
    y = {}
    for c in centers:
        y[c] = m.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = m.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    m.update()

    # Demand constraints: meet exact demand for each store
    for s in stores:
        m.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # Capacity constraints: shipments from a center cannot exceed its capacity if opened
    for c in centers:
        m.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_term = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    m.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Flatten variables into required dict with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[c][s]

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_val = model.ObjVal if model.Status == GRB.OPTIMAL or model.Status == GRB.TIME_LIMIT else None

    # Build solution dictionary with all variable values
    solution = {}
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(objective_val) if objective_val is not None else None,
        "solution": solution
    }