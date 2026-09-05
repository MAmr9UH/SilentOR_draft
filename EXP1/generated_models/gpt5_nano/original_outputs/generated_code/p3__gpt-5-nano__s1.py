import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    shift_starts = data["shift_start_times"]
    period_starts = data["period_start_times"]
    demand_by_period = data["demand_by_period_start"]

    # Create variables: s2, s6, s10, s14, s18, s22
    variables = {}
    for t in shift_starts:
        key = f"s{t}"
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
        variables[key] = v

    model.update()

    # Helper to determine if a shift starting at t covers the period starting at p
    def covers(t: int, p: int) -> bool:
        shift_hours = [(t + i) % 24 for i in range(8)]
        period_hours = [(p + j) % 24 for j in range(4)]
        return not set(shift_hours).isdisjoint(period_hours)

    # Constraints: meet demand for each period
    for p in period_starts:
        demand = int(demand_by_period[str(p)])
        expr = gp.LinExpr()
        for t in shift_starts:
            if covers(t, p):
                expr += variables[f"s{t}"]
        model.addConstr(expr >= demand, name=f"cover_p{p}")

    # Objective: minimize total number of starting salespeople
    model.setObjective(gp.quicksum(variables[f"s{t}"] for t in shift_starts), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Prepare status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    model.update()
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
        "objective": float(model.ObjVal),
        "solution": solution
    }