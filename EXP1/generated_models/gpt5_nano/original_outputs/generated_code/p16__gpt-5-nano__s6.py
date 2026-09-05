import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    # Extract data
    centers = data["centers"]  # e.g., ["c1", ..., "c7"]
    stores = data["stores"]    # e.g., ["s1", ..., "s4"]
    opening_cost = data["fixed_opening_cost"]  # dict: c1 -> cost
    transport_cost = data["transport_cost"]     # dict: c -> {s: cost}
    demand = data["demand"]                     # dict: s -> demand
    capacity = data["capacity"]                 # dict: c -> capacity

    model = gp.Model("SupplyTek")

    # Decision variables
    y = {}  # binary: open center
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}  # shipment from center c to store s
    for c in centers:
        for s in stores:
            f[(c, s)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    model.update()

    # Objective: opening costs + transportation costs
    obj = quicksum(opening_cost[c] * y[c] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * f[(c, s)]
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction
    for s in stores:
        model.addConstr(quicksum(f[(c, s)] for c in centers) == demand[s], name=f"demand_{s}")

    # Capacity with linking to open decision
    for c in centers:
        model.addConstr(quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Prepare variables dict to return
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    # Collect solution values for all variables
    variable_keys = [
        "y_c1","y_c2","y_c3","y_c4","y_c5","y_c6","y_c7",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4",
        "f_c6_s1","f_c6_s2","f_c6_s3","f_c6_s4",
        "f_c7_s1","f_c7_s2","f_c7_s3","f_c7_s4"
    ]

    solution = {}
    for key in variable_keys:
        solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }