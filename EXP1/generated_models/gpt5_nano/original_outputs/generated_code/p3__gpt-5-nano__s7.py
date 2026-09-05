import gurobipy as gp

def build_model(data: dict) -> tuple:
    m = gp.Model()

    shifts = list(data.get("shift_start_times", []))
    period_starts = list(data.get("period_start_times", []))
    shift_len = int(data.get("shift_length_hours", 8))
    period_len = int(data.get("period_length_hours", 4))

    # Create integer decision variables for each shift start time
    var_by_start = {}
    for s in shifts:
        v = m.addVar(vtype=gp.GRB.INTEGER, name=f"s{int(s)}", lb=0)
        var_by_start[int(s)] = v
    m.update()

    demand_map = data.get("demand_by_period_start", {})

    def overlaps(s: int, t: int) -> bool:
        L = period_len
        for k in (0, 24):
            a = s
            b = s + shift_len
            c = t
            d = t + L
            start = max(a, c + k)
            end = min(b, d + k)
            if end > start:
                return True
        return False

    # Add constraints for each period
    for t in period_starts:
        demand = demand_map.get(str(t), demand_map.get(t, 0))
        expr = gp.quicksum(var_by_start[s] for s in shifts if overlaps(int(s), int(t)))
        m.addConstr(expr >= demand)

    # Objective: minimize total number of salespeople
    m.setObjective(gp.quicksum(var_by_start[s] for s in shifts), gp.GRB.MINIMIZE)

    # Prepare variables dictionary with exact required keys
    variables = {
        "s2": var_by_start[2],
        "s6": var_by_start[6],
        "s10": var_by_start[10],
        "s14": var_by_start[14],
        "s18": var_by_start[18],
        "s22": var_by_start[22],
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    if status_num == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_num == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_num == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_num == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_num == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_num)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {
        "s2": float(variables["s2"].X),
        "s6": float(variables["s6"].X),
        "s10": float(variables["s10"].X),
        "s14": float(variables["s14"].X),
        "s18": float(variables["s18"].X),
        "s22": float(variables["s22"].X),
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }