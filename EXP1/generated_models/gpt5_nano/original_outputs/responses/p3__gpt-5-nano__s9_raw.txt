from gurobipy import *

def build_model(data: dict) -> tuple:
    model = Model()

    # Extract data
    shift_starts = data["shift_start_times"]
    period_starts = data["period_start_times"]
    period_len = data["period_length_hours"]
    shift_len = data["shift_length_hours"]
    demand = data["demand_by_period_start"]

    # Decision variables: number of staff starting at each shift
    s2  = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s6  = model.addVar(vtype=GRB.INTEGER, lb=0, name="s6")
    s10 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s10")
    s14 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s14")
    s18 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s18")
    s22 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s22")

    # Objective: minimize total number of salespeople employed
    model.setObjective(s2 + s6 + s10 + s14 + s18 + s22, GRB.MINIMIZE)

    # Map for convenient access
    var_by_start = {2: s2, 6: s6, 10: s10, 14: s14, 18: s18, 22: s22}

    # Constraints: ensure each period's demand is met
    for p in period_starts:
        d = int(demand[str(p)])
        overlapping_sum = 0
        for t in shift_starts:
            # Check overlap of [t, t+8) with [p, p+4)
            if not (t >= p + period_len or t + shift_len <= p):
                overlapping_sum += var_by_start[t]
        model.addConstr(overlapping_sum >= d, name=f"cover_p{p}")

    model.update()
    variables = {
        "s2": s2,
        "s6": s6,
        "s10": s10,
        "s14": s14,
        "s18": s18,
        "s22": s22
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Read status and objective
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
    elif status_code == GRB.SUBOPTIMAL:
        status_str = "SUBOPTIMAL"
    else:
        status_str = str(status_code)

    obj_val = model.ObjVal if model.ObjVal is not None else float('nan')

    # Solution values
    solution = {
        "s2": int(variables["s2"].X),
        "s6": int(variables["s6"].X),
        "s10": int(variables["s10"].X),
        "s14": int(variables["s14"].X),
        "s18": int(variables["s18"].X),
        "s22": int(variables["s22"].X)
    }

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }