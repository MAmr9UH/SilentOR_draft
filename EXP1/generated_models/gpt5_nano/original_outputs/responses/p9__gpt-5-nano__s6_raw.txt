import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    days = data.get("days", [])
    needs = data.get("employees_needed", [])
    n = len(days) if days else 7  # default to 7 if not provided

    # Decision variables: number starting on each day s0..s6
    s_vars = {}
    for d in range(n):
        s_vars[f"s{d}"] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{d}")

    m.update()

    # Objective: minimize total number of employees hired
    m.setObjective(gp.quicksum(s_vars[f"s{d}"] for d in range(n)), GRB.MINIMIZE)

    # Constraints: for each day t, coverage by workers started on days t, t-1, ..., t-4
    for t in range(n):
        involved = [ (t - k) % n for k in range(5) ]
        m.addConstr(gp.quicksum(s_vars[f"s{i}"] for i in involved) >= needs[t], name=f"cover_day_{t}")

    return m, s_vars

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

    model.update()
    solution = {}
    for d in range(len(days := data.get("days", [])) or 7):
        key = f"s{d}"
        solution[key] = int(round(variables[key].X))

    # Ensure we return 7 entries even if days was shorter
    if len(solution) < 7:
        for d in range(len(solution), 7):
            solution[f"s{d}"] = 0

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }