import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build and return the optimization model along with a dictionary of decision variables.
    """
    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1","s2","s3","s4","s5","s6","s7","s8"]

    fixed_opening_cost = data["fixed_opening_cost"]  # dict: {"c1": ..., "c2": ..., ...}
    transport_cost = data["transport_cost"]          # dict: {"c1": {"s1": ..., ...}, ...}
    demand = data["demand"]                          # dict: {"s1": ..., ..., "s8": ...}
    capacity = data["capacity"]                      # dict: {"c1": ..., "c2": ..., ...}

    model = gp.Model()

    # Decision variables
    variables_keys = {}

    # Binary opening variables
    for c in centers:
        v = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")
        variables_keys[f"y_{c}"] = v

    # Transportation variables
    for c in centers:
        for s in stores:
            v = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")
            variables_keys[f"f_{c}_{s}"] = v

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost_expr = gp.quicksum(fixed_opening_cost[c] * variables_keys[f"y_{c}"] for c in centers)
    transport_cost_expr = gp.quicksum(
        transport_cost[c][s] * variables_keys[f"f_{c}_{s}"] for c in centers for s in stores
    )
    model.setObjective(opening_cost_expr + transport_cost_expr, gp.GRB.MINIMIZE)

    # Constraints

    # Demand constraints: sum over centers of f_{c,s} >= demand_s
    for s in stores:
        model.addConstr(gp.quicksum(variables_keys[f"f_{c}_{s}"] for c in centers) >= demand[s], name=f"Demand_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        model.addConstr(gp.quicksum(variables_keys[f"f_{c}_{s}"] for s in stores) <= capacity[c] * variables_keys[f"y_{c}"],
                        name=f"Cap_{c}")

    # Return the model and the dictionary of variables
    variables = {
        "variables_keys": variables_keys,
        "note": "Scalar variables under EXACTLY these flat keys. The returned solution uses the same keys."
    }

    return model, variables

def _status_to_string(status: int) -> str:
    try:
        if status == gp.GRB.OPTIMAL:
            return "OPTIMAL"
        if status == gp.GRB.INFEASIBLE:
            return "INFEASIBLE"
        if status == gp.GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if status == gp.GRB.UNBOUNDED:
            return "UNBOUNDED"
        if status == gp.GRB.TIME_LIMIT:
            return "TIME_LIMIT"
    except Exception:
        pass
    return str(status)

def solve(data: dict) -> dict:
    """
    Build, solve the model, and return the solution in the specified schema.
    """
    model, variables = build_model(data)
    model.optimize()

    status_str = _status_to_string(model.Status)
    obj_val = float(model.ObjVal)

    # Order of keys as required
    order = [
        "y_c1","y_c2","y_c3","y_c4",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5","f_c1_s6","f_c1_s7","f_c1_s8",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5","f_c2_s6","f_c2_s7","f_c2_s8",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5","f_c3_s6","f_c3_s7","f_c3_s8",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5","f_c4_s6","f_c4_s7","f_c4_s8"
    ]

    solution_values = {}
    for key in order:
        solution_values[key] = float(variables["variables_keys"][key].X)

    solution = solution_values

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }