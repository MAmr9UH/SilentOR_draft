import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    days = 7
    needs = data["employees_needed"]

    # Decision variables: number of workers starting on each day
    s = {}
    for i in range(days):
        s[i] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{i}")

    model.update()

    # Coverage constraints: each day must be covered by workers starting in the previous 4 days and today
    for i in range(days):
        idxs = [(i - k) % days for k in range(5)]
        model.addConstr(gp.quicksum(s[j] for j in idxs) >= needs[i], name=f"cover_day_{i}")

    # Objective: minimize total number of workers started in the week
    model.setObjective(gp.quicksum(s[i] for i in range(days)), GRB.MINIMIZE)
    model.update()

    variables = {f"s{i}": s[i] for i in range(days)}
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_num == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_num)

    objective = model.ObjVal
    solution = {f"s{i}": variables[f"s{i}"].X for i in range(7)}

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }