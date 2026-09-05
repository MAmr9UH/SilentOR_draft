import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    # Variable definitions
    var_names = ["s2", "s6", "s10", "s14", "s18", "s22"]
    starts = {"s2": 2, "s6": 6, "s10": 10, "s14": 14, "s18": 18, "s22": 22}
    variables = {}
    for name in var_names:
        variables[name] = model.addVar(vtype=GRB.INTEGER, lb=0, name=name)
    model.update()

    # Data extraction
    shift_len = int(data["shift_length_hours"])
    period_len = int(data["period_length_hours"])
    period_starts = data["period_start_times"]
    demands = data["demand_by_period_start"]

    # Helper for time interval overlaps with wrap-around at 24 hours
    def intervals(start, length):
        end = start + length
        if end <= 24:
            return [(start, end)]
        else:
            return [(start, 24), (0, end - 24)]

    def overlaps(shift_start, period_start, Lshift, Lperiod):
        for a, b in intervals(shift_start, Lshift):
            for c, d in intervals(period_start, Lperiod):
                left = max(a, c)
                right = min(b, d)
                if left < right:
                    return True
        return False

    # Add constraints: for each period, sum of overlapping starting shifts >= demand
    for pstart in period_starts:
        demand = int(demands[str(pstart)])
        terms = []
        for name in var_names:
            if overlaps(starts[name], pstart, shift_len, period_len):
                terms.append(variables[name])
        model.addConstr(gp.quicksum(terms) >= demand, name=f"cov_{pstart}")

    # Objective: minimize total number of starting salespeople
    model.setObjective(gp.quicksum(variables[name] for name in var_names), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NUMERIC: "NUMERIC"
    }
    status = status_map.get(model.Status, str(model.Status))
    model.update()

    obj = model.ObjVal
    solution = {k: int(round(variables[k].X)) for k in ["s2", "s6", "s10", "s14", "s18", "s22"]}

    return {
        "status": status,
        "objective": float(obj) if obj is not None else None,
        "solution": solution
    }