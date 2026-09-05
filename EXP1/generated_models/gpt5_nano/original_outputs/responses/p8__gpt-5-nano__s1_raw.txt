import gurobipy as gp

def build_model(data: dict) -> tuple:
    m = gp.Model()
    # Create decision variables: integer workers per shift, non-negative
    s1 = m.addVar(vtype=gp.GRB.INT, name="s1", lb=0)
    s2 = m.addVar(vtype=gp.GRB.INT, name="s2", lb=0)
    s3 = m.addVar(vtype=gp.GRB.INT, name="s3", lb=0)
    s4 = m.addVar(vtype=gp.GRB.INT, name="s4", lb=0)
    m.update()

    var_map = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    requirements = data["workers_required_by_window"]
    shift_cov = data["shift_coverage"]

    # Constraints: for each 3-hour window, sum of covering shifts >= required workers
    for w in range(8):
        expr = 0
        for i in range(1, 5):
            cov = shift_cov[str(i)]
            if w in cov:
                expr += var_map[f"s{i}"]
        m.addConstr(expr >= requirements[w], name=f"cov_w{w}")

    # Objective: minimize total wage cost
    wage = data["shift_wage"]
    m.setObjective(
        s1 * wage["1"] + s2 * wage["2"] + s3 * wage["3"] + s4 * wage["4"],
        gp.GRB.MINIMIZE
    )

    return m, {"s1": s1, "s2": s2, "s3": s3, "s4": s4}


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_code == gp.GRB.SUBOPTIMAL:
        status_str = "SUBOPTIMAL"
    else:
        status_str = str(status_code)

    model.update()
    s1_val = variables["s1"].X
    s2_val = variables["s2"].X
    s3_val = variables["s3"].X
    s4_val = variables["s4"].X

    solution = {
        "s1": s1_val,
        "s2": s2_val,
        "s3": s3_val,
        "s4": s4_val
    }

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }