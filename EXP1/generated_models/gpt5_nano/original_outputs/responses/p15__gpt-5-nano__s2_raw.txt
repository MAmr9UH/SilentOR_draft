import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("Distribution_Dynamics")

    # Decision variables
    y_vars = {}
    for c in centers:
        key = f"y_{c}"
        y_vars[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f_vars = {}
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            f_vars[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.quicksum(opening_cost[c] * y_vars[f"y_{c}"] for c in centers)
    obj += gp.quicksum(transport_cost[c][s] * f_vars[f"{c}_{s}"] for c in centers for s in stores)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction: sum_c f_c_s = demand_s for each store s
    demand = data["demand"]
    for s in stores:
        model.addConstr(
            gp.quicksum(f_vars[f"{c}_{s}"] for c in centers) == demand[s],
            name=f"demand_{s}"
        )

    # 2) Capacity constraints: sum_s f_c_s <= capacity_c * y_c for each center c
    capacity = data["capacity"]
    for c in centers:
        model.addConstr(
            gp.quicksum(f_vars[f"{c}_{s}"] for s in stores) <= capacity[c] * y_vars[f"y_{c}"],
            name=f"cap_{c}"
        )

    # Return model and a flat variables dictionary with exact keys
    variables = {}
    for c in centers:
        key = f"y_{c}"
        variables[key] = y_vars[key]
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = f_vars[key]

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(stat)

    objective = float(model.ObjVal)

    solution = {}
    for key in sorted(variables.keys()):
        # Each value is a Var; fetch its optimized value
        var = variables[key]
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }