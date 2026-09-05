import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {}

    # Decision variables: y_c (opening) - binary
    for c in data["centers"]:
        key = f"y_{c}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Decision variables: f_c_s (shipments) - continuous, nonnegative
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s = demand_s
    for s in data["stores"]:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for c in data["centers"])
        model.addConstr(expr == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in data["centers"]:
        expr = gp.quicksum(variables[f"f_{c}_{s}"] for s in data["stores"])
        model.addConstr(expr <= data["capacity"][c] * variables[f"y_{c}"], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in data["centers"])
    transport_cost = gp.quicksum(data["transport_cost"][c][s] * variables[f"f_{c}_{s}"]
                                 for c in data["centers"] for s in data["stores"])
    model.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string
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

    # Read solution values
    solution = {}
    order = [
        "y_c1","y_c2","y_c3","y_c4",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5","f_c1_s6",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5","f_c2_s6",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5","f_c3_s6",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5","f_c4_s6",
    ]
    for key in order:
        solution[key] = variables[key].X

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result