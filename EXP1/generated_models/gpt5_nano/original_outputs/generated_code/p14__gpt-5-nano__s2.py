import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    m = gp.Model("LogiChain")

    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1","s2",...,"s8"]

    # Decision variables
    y = {}
    for c in centers:
        y[c] = m.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    m.update()

    # Objective: minimize opening costs plus transportation costs
    transport_cost_sum = gp.quicksum(data["transport_cost"][c][s] * f[c][s] for c in centers for s in stores)
    opening_cost_sum = gp.quicksum(data["fixed_opening_cost"][c] * y[c] for c in centers)
    m.setObjective(transport_cost_sum + opening_cost_sum, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for s in stores:
        m.addConstr(gp.quicksum(f[c][s] for c in centers) == data["demand"][s], name=f"Demand_{s}")

    # Capacity constraints (cannot ship from a closed center)
    for c in centers:
        m.addConstr(gp.quicksum(f[c][s] for s in stores) <= data["capacity"][c] * y[c], name=f"Cap_{c}")

    # Build flat variables dictionary to return
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

    obj_val = model.ObjVal

    # Build solution dict with exact keys
    solution = {}
    for c in data["centers"]:
        key = f"y_{c}"
        solution[key] = variables[key].X
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = variables[key].X

    return {
        "type": "object",
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }