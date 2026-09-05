import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    need = list(data["employees_needed"])
    work_days = int(data.get("work_days_consecutive", 5))

    model = gp.Model()

    # Decision variables: s0..s6 = workers starting on each day
    s = {}
    for i in range(7):
        s[i] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{i}")

    model.update()

    # Constraints: For each day d, sum of starts on days d-4..d (mod 7) >= need[d]
    for d in range(7):
        start_indices = [(d - r) % 7 for r in range(work_days)]
        model.addConstr(gp.quicksum(s[t] for t in start_indices) >= need[d], name=f"cover_day_{d}")

    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(s[i] for i in range(7)), GRB.MINIMIZE)

    variables = {f"s{i}": s[i] for i in range(7)}
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

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
    else:
        status_str = str(status_code)

    obj_val = float(model.ObjVal)

    solution = {f"s{i}": float(variables[f"s{i}"].X) for i in range(7)}

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }