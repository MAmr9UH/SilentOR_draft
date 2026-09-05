import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    centers = data["centers"]  # e.g., ["c1", ..., "c7"]
    stores = data["stores"]    # e.g., ["s1", ..., "s5"]

    fixed_opening_cost = data["fixed_opening_cost"]  # dict: "c1": value
    transport_cost = data["transport_cost"]          # dict: "c1": {"s1": cost, ...}
    demand = data["demand"]                          # dict: "s1": value
    capacity = data["capacity"]                      # dict: "c1": value

    model = gp.Model()

    # Decision variables
    # y_c: 1 if center c is opened
    y = {}
    for c in centers:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    # f_c_s: amount shipped from center c to store s
    f = {}
    for c in centers:
        f[c] = {}
        for s in stores:
            f[c][s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = gp.quicksum(fixed_opening_cost[c] * y[c] for c in centers)
    transport_costs = gp.quicksum(transport_cost[c][s] * f[c][s] for c in centers for s in stores)
    model.setObjective(opening_costs + transport_costs, GRB.MINIMIZE)

    # Constraints
    # 1) Demand at each store must be met
    for s in stores:
        model.addConstr(gp.quicksum(f[c][s] for c in centers) == demand[s], name=f"dem_{s}")

    # 2) Shipments from a center cannot exceed its capacity if center is opened
    for c in centers:
        model.addConstr(gp.quicksum(f[c][s] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    # Return model and a flat dictionary of all variables with the required keys
    variables = {}

    # y variables
    for c in centers:
        key = f"y_{c}"
        variables[key] = y[c]

    # f variables
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = f[c][s]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = model.Status
    status_text = status_map.get(status, str(status))

    objective_value = float(model.ObjVal)

    # Build solution dictionary with exactly the required keys
    solution = {}

    # y variables in order y_c1 ... y_c7
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    # f variables in order f_c1_s1 ... f_c7_s5
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_text,
        "objective": objective_value,
        "solution": solution
    }