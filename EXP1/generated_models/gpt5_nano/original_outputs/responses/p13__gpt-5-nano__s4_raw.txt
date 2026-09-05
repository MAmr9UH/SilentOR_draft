import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1","s2","s3","s4","s5","s6"]

    opening_cost = data["fixed_opening_cost"]  # dict: {"c1": ..., ...}
    transport_cost = data["transport_cost"]     # dict: {"c1": {"s1": ..., ...}, ...}
    demand = data["demand"]                    # dict: {"s1": ..., ...}
    capacity = data["capacity"]                # dict: {"c1": ..., ...}

    # Decision variables
    y = {}  # binary: open center
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}  # continuous: shipment from center c to store s
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_term = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Constraints: meet exact demand at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # Constraints: center capacity cannot be exceeded if not opened
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Flattened variable dictionary to return (exact keys required)
    variables = {
        "y_c1": y["c1"],
        "y_c2": y["c2"],
        "y_c3": y["c3"],
        "y_c4": y["c4"],
    }
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(st)

    objective_value = float(model.ObjVal)

    solution = {}
    # Fill y variables
    solution["y_c1"] = float(variables["y_c1"].X)
    solution["y_c2"] = float(variables["y_c2"].X)
    solution["y_c3"] = float(variables["y_c3"].X)
    solution["y_c4"] = float(variables["y_c4"].X)

    # Fill f variables
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }