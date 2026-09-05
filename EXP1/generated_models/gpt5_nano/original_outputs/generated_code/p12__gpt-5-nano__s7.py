import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]  # e.g., ["c1","c2","c3","c4","c5"]
    stores = data["stores"]    # e.g., ["s1","s2","s3","s4","s5"]

    opening_costs = data["fixed_opening_cost"]
    transport_costs = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    variables = {}

    # Binary opening variables y_c for each center
    for c_label in centers:
        key = f"y_{c_label}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Transportation variables f_{c}_{s}
    for c_label in centers:
        for s_label in stores:
            key = f"f_{c_label}_{s_label}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj = gp.LinExpr()
    for c_label in centers:
        y_var = variables[f"y_{c_label}"]
        obj += opening_costs[c_label] * y_var
    for c_label in centers:
        for s_label in stores:
            f_var = variables[f"f_{c_label}_{s_label}"]
            obj += transport_costs[c_label][s_label] * f_var
    model.setObjective(obj, GRB.MINIMIZE)

    # Demand constraints: for each store s, sum_c f_{c}_{s} = demand_s
    for s_label in stores:
        lhs = gp.LinExpr()
        for c_label in centers:
            lhs += variables[f"f_{c_label}_{s_label}"]
        model.addConstr(lhs == demand[s_label])

    # Capacity constraints: for each center c, sum_s f_{c}_{s} <= capacity_c * y_c
    for c_label in centers:
        lhs = gp.LinExpr()
        for s_label in stores:
            lhs += variables[f"f_{c_label}_{s_label}"]
        model.addConstr(lhs <= capacity[c_label] * variables[f"y_{c_label}"])

    return model, variables

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
    for i in range(1, 6):
        key = f"y_c{i}"
        solution[key] = variables[key].X
    for c in range(1, 6):
        for s in range(1, 6):
            key = f"f_c{c}_s{s}"
            solution[key] = variables[key].X

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }