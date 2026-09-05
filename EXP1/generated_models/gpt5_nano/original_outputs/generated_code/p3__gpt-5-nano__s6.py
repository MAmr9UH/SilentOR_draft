import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    # Decision variables: number starting at each shift time
    s2 = model.addVar(vtype=GRB.INTEGER, name="s2")
    s6 = model.addVar(vtype=GRB.INTEGER, name="s6")
    s10 = model.addVar(vtype=GRB.INTEGER, name="s10")
    s14 = model.addVar(vtype=GRB.INTEGER, name="s14")
    s18 = model.addVar(vtype=GRB.INTEGER, name="s18")
    s22 = model.addVar(vtype=GRB.INTEGER, name="s22")

    model.update()

    # Demand data
    period_start_times = data.get("period_start_times", [])
    demand_by_period_start = data.get("demand_by_period_start", {})

    demand = {}
    for p in period_start_times:
        demand[p] = demand_by_period_start.get(str(p), 0)

    # Constraints per period (two overlapping shifts cover each period)
    for p in period_start_times:
        if p == 2:
            model.addConstr(s2 + s22 >= demand[p], name=f"demand_{p}")
        elif p == 6:
            model.addConstr(s2 + s6 >= demand[p], name=f"demand_{p}")
        elif p == 10:
            model.addConstr(s6 + s10 >= demand[p], name=f"demand_{p}")
        elif p == 14:
            model.addConstr(s10 + s14 >= demand[p], name=f"demand_{p}")
        elif p == 18:
            model.addConstr(s14 + s18 >= demand[p], name=f"demand_{p}")
        elif p == 22:
            model.addConstr(s18 + s22 >= demand[p], name=f"demand_{p}")

    # Objective: minimize total number of salespeople
    model.setObjective(s2 + s6 + s10 + s14 + s18 + s22, GRB.MINIMIZE)

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

    status_int = model.Status
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

    obj_val = model.ObjVal

    solution = {}
    for key, var in variables.items():
        val = var.X
        solution[key] = int(val) if val is not None else None

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }