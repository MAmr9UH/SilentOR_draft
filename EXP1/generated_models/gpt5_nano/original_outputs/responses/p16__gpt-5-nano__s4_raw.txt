import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    model = gp.Model()

    # Decision variables
    y = {}  # open/close decision for centers
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}  # shipments from center c to store s
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    model.setObjective(
        gp.quicksum(opening_cost[c] * y[c] for c in centers) +
        gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores),
        sense=GRB.MINIMIZE
    )

    # Demand constraints: meet demand at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity constraints: cannot ship more than capacity if center is open
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Flatten variables into required keys
    variables = {}
    for i, c in enumerate(centers, start=1):
        key = f"y_c{i}"
        variables[key] = y[c]
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = f[c][s]

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

    # Build solution dictionary with all required keys
    solution = {}
    for i in range(1, 8):
        key = f"y_c{i}"
        solution[key] = float(variables[key].X)

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