from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    from gurobipy import Model, GRB, quicksum
    model = Model()
    
    # Decision variables: integers (non-negative) representing workers on each shift
    s1 = model.addVar(vtype=GRB.INTEGER, name="s1", lb=0)
    s2 = model.addVar(vtype=GRB.INTEGER, name="s2", lb=0)
    s3 = model.addVar(vtype=GRB.INTEGER, name="s3", lb=0)
    s4 = model.addVar(vtype=GRB.INTEGER, name="s4", lb=0)
    
    model.update()
    
    required = data["workers_required_by_window"]
    coverage = data["shift_coverage"]  # dict with keys "1","2","3","4" and lists of windows
    
    var_by_shift = {"1": s1, "2": s2, "3": s3, "4": s4}
    
    # Constraints: for each window, sum of covering shifts >= required workers
    for w in range(8):
        expr = 0
        for shift_key, windows in coverage.items():
            if w in windows:
                expr += var_by_shift[shift_key]
        model.addConstr(expr >= required[w], name=f"cover_w{w}")
    
    # Objective: minimize total wage
    obj = (
        data["shift_wage"]["1"] * s1 +
        data["shift_wage"]["2"] * s2 +
        data["shift_wage"]["3"] * s3 +
        data["shift_wage"]["4"] * s4
    )
    model.setObjective(obj, GRB.MINIMIZE)
    
    return model, {"s1": s1, "s2": s2, "s3": s3, "s4": s4}


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Map status to a string label
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }
    status_str = status_map.get(status_code, str(status_code))
    
    # Read objective value and variable values
    try:
        obj_val = float(model.ObjVal)
    except:
        obj_val = None
    
    s_vals = {}
    for k in ["s1", "s2", "s3", "s4"]:
        try:
            s_vals[k] = float(variables[k].X)
        except:
            s_vals[k] = None
    
    # Build solution dictionary following the required JSON-like schema
    solution = {
        "s1": s_vals["s1"],
        "s2": s_vals["s2"],
        "s3": s_vals["s3"],
        "s4": s_vals["s4"]
    }
    
    return {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number"},
            "solution": {
                "type": "object",
                "required": ["s1", "s2", "s3", "s4"],
                "properties": {
                    "s1": {"type": "number"},
                    "s2": {"type": "number"},
                    "s3": {"type": "number"},
                    "s4": {"type": "number"}
                }
            }
        },
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }