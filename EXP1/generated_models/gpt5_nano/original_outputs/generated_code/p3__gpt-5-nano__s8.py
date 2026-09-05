import gurobipy as gp

def build_model(data: dict) -> tuple:
    m = gp.Model()
    m.setParam('OutputFlag', 0)

    # Demands per 4-hour period starting times
    demand_by_period_start = data.get("demand_by_period_start", {})
    demands = {int(k): int(v) for k, v in demand_by_period_start.items()}

    # Shift start times and corresponding variable keys
    starts = [2, 6, 10, 14, 18, 22]
    var_keys = ["s2", "s6", "s10", "s14", "s18", "s22"]

    # DecisionVariables: number of salespeople starting at each shift
    variables = {}
    for key, st in zip(var_keys, starts):
        v = m.addVar(vtype=gp.GRB.INTEGER, lb=0, name=key)
        variables[key] = v

    m.update()

    # Objective: minimize total number of salespeople
    m.setObjective(gp.quicksum(variables[k] for k in var_keys), gp.GRB.MINIMIZE)

    # Coverage constraints per 4-hour period
    coverage = {
        2: ["s2", "s22"],
        6: ["s2", "s6"],
        10: ["s6", "s10"],
        14: ["s10", "s14"],
        18: ["s14", "s18"],
        22: ["s18", "s22"]
    }

    for p in starts:
        d_p = demands.get(p, 0)
        m.addConstr(gp.quicksum(variables[name] for name in coverage[p]) >= d_p, name=f"cover_{p}")

    return m, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    # Map status to string using GRB constants
    from gurobipy import GRB
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    objective = float(model.ObjVal)

    solution_vals = {
        "s2": float(variables["s2"].X),
        "s6": float(variables["s6"].X),
        "s10": float(variables["s10"].X),
        "s14": float(variables["s14"].X),
        "s18": float(variables["s18"].X),
        "s22": float(variables["s22"].X),
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution_vals
    }