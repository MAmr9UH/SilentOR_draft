def build_model(data: dict):
    from gurobipy import Model, GRB

    m = Model()
    # Decision variables: number of salespeople starting at each shift time
    s2 = m.addVar(vtype=GRB.INTEGER, name="s2")
    s6 = m.addVar(vtype=GRB.INTEGER, name="s6")
    s10 = m.addVar(vtype=GRB.INTEGER, name="s10")
    s14 = m.addVar(vtype=GRB.INTEGER, name="s14")
    s18 = m.addVar(vtype=GRB.INTEGER, name="s18")
    s22 = m.addVar(vtype=GRB.INTEGER, name="s22")

    m.update()

    variables = {
        "s2": s2,
        "s6": s6,
        "s10": s10,
        "s14": s14,
        "s18": s18,
        "s22": s22
    }

    # Build coverage constraints:
    # For each period start p, demand must be met by workers starting at p and at the previous period (p-4)
    shift_starts = data["shift_start_times"]  # [2, 6, 10, 14, 18, 22]
    demand_by_period_start = data["demand_by_period_start"]  # keys are strings, e.g., "2": 10

    var_map = {
        "2": s2,
        "6": s6,
        "10": s10,
        "14": s14,
        "18": s18,
        "22": s22
    }

    for p in shift_starts:
        p_int = int(p)
        prev = 22 if p_int == 2 else p_int - 4
        p_key = str(p_int)
        prev_key = str(prev)
        demand = demand_by_period_start[p_key]
        m.addConstr(var_map[p_key] + var_map[prev_key] >= demand, name=f"cover_{p_int}_{prev}")

    m.update()
    m.setObjective(s2 + s6 + s10 + s14 + s18 + s22, GRB.MINIMIZE)
    m.update()

    return m, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    from gurobipy import GRB

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

    obj = model.ObjVal

    solution = {
        "s2": int(variables["s2"].X),
        "s6": int(variables["s6"].X),
        "s10": int(variables["s10"].X),
        "s14": int(variables["s14"].X),
        "s18": int(variables["s18"].X),
        "s22": int(variables["s22"].X)
    }

    return {
        "status": status,
        "objective": float(obj),
        "solution": solution
    }