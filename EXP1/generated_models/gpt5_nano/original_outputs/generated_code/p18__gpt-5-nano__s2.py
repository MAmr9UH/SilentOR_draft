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
    # y_c: binary indicator if center c is opened
    y = {}
    variables = {}
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y[c] = var
        variables[f"y_{c}"] = var

    # f_c_s: flow from center c to store s
    f = {}
    for c in centers:
        for s in stores:
            var = model.addVar(lb=0.0, ub=demand[s], vtype=GRB.CONTINUOUS, name=f"f_{c}_{s}")
            f[f"{c}_{s}"] = var
            variables[f"f_{c}_{s}"] = var

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_expr = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_expr = gp.quicksum(transport_cost[c][s] * f[f"{c}_{s}"] for c in centers for s in stores)
    model.setObjective(opening_expr + transport_expr, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction at each store
    for s in stores:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for c in centers) == demand[s], name=f"demand_{s}")

    # 2) Center capacity constraints linking to opening decision
    for c in centers:
        model.addConstr(gp.quicksum(f[f"{c}_{s}"] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    return model, variables

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

    objective_val = model.ObjVal if model.ObjVal is not None else 0.0

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "type": "object",
        "status": status_str,
        "objective": float(objective_val),
        "solution": solution
    }