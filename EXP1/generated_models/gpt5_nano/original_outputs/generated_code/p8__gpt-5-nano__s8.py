def build_model(data: dict) -> tuple:
    import gurobipy as gp

    model = gp.Model()

    # Decision variables: number of workers on each shift (non-negative integers)
    s1 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s4")

    model.update()

    # Data extraction
    required_by_window = data["workers_required_by_window"]  # list of length 8
    coverage_data = data["shift_coverage"]  # keys "1","2","3","4"

    coverage = {
        1: list(map(int, coverage_data["1"])),
        2: list(map(int, coverage_data["2"])),
        3: list(map(int, coverage_data["3"])),
        4: list(map(int, coverage_data["4"])),
    }

    # Constraints: for each window, sum of covering shifts >= required workers
    for w in range(8):
        req = int(required_by_window[w])
        expr = 0
        if w in coverage[1]:
            expr += s1
        if w in coverage[2]:
            expr += s2
        if w in coverage[3]:
            expr += s3
        if w in coverage[4]:
            expr += s4
        model.addConstr(expr >= req)

    # Objective: minimize total wage cost
    wages = {
        1: int(data["shift_wage"]["1"]),
        2: int(data["shift_wage"]["2"]),
        3: int(data["shift_wage"]["3"]),
        4: int(data["shift_wage"]["4"]),
    }
    model.setObjective(s1 * wages[1] + s2 * wages[2] + s3 * wages[3] + s4 * wages[4], gp.GRB.MINIMIZE)

    variables = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    return model, variables

def solve(data: dict) -> dict:
    import gurobipy as gp

    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.FEASIBLE: "FEASIBLE",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.CUTOFF: "CUTOFF",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status, str(status))

    obj_val = model.ObjVal
    objective = float(obj_val) if obj_val is not None else None

    s1_val = float(variables["s1"].X)
    s2_val = float(variables["s2"].X)
    s3_val = float(variables["s3"].X)
    s4_val = float(variables["s4"].X)

    solution = {"s1": s1_val, "s2": s2_val, "s3": s3_val, "s4": s4_val}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }