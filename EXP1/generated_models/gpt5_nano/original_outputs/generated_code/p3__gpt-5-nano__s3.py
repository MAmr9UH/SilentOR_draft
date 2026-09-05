import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Unpack data
    shift_starts = data["shift_start_times"]        # e.g., [2, 6, 10, 14, 18, 22]
    shift_length = data["shift_length_hours"]       # 8
    period_starts = data["period_start_times"]      # e.g., [2, 6, 10, 14, 18, 22]
    period_length = data["period_length_hours"]     # 4
    demand_by_period_start = data["demand_by_period_start"]  # dict with string keys

    # Build demand per hour (0..23)
    demand_by_hour = {h: 0 for h in range(24)}
    for p in period_starts:
        d = demand_by_period_start[str(p)]
        for i in range(period_length):
            h = (p + i) % 24
            demand_by_hour[h] = d

    # Create decision variables: number starting at each shift start
    var_by_start = {}
    for s in shift_starts:
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{int(s)}")
        var_by_start[s] = v

    model.update()

    # Coverage sets: which hours are covered by each shift start
    coverage = {}
    for s in shift_starts:
        coverage[s] = set((s + j) % 24 for j in range(shift_length))

    # Constraints: for every hour, total on-duty staff must meet demand
    for h in range(24):
        demand = demand_by_hour[h]
        expr = gp.LinExpr()
        for s in shift_starts:
            if h in coverage[s]:
                expr += var_by_start[s]
        model.addConstr(expr >= demand)

    # Prepare variables dict to return with exact keys required
    variables = {
        "s2": var_by_start[2],
        "s6": var_by_start[6],
        "s10": var_by_start[10],
        "s14": var_by_start[14],
        "s18": var_by_start[18],
        "s22": var_by_start[22]
    }

    return model, variables

def _status_to_string(st: int) -> str:
    if st == GRB.OPTIMAL:
        return "OPTIMAL"
    if st == GRB.INFEASIBLE:
        return "INFEASIBLE"
    if st == GRB.UNBOUNDED:
        return "UNBOUNDED"
    if st == GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if st == GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    return str(st)

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    model.update()
    status_str = _status_to_string(model.Status)
    objective_val = float(model.ObjVal)

    solution = {
        "s2": int(round(variables["s2"].X)),
        "s6": int(round(variables["s6"].X)),
        "s10": int(round(variables["s10"].X)),
        "s14": int(round(variables["s14"].X)),
        "s18": int(round(variables["s18"].X)),
        "s22": int(round(variables["s22"].X)),
    }

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }