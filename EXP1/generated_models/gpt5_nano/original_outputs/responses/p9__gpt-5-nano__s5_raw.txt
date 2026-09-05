import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    need = data["employees_needed"]
    n_days = len(need)
    work_days_consecutive = data["work_days_consecutive"]

    model = gp.Model()

    # Decision variables: number of workers starting on each day s0..s6 (or s0..s{n_days-1})
    s = {}
    for i in range(n_days):
        s[i] = model.addVar(vtype=GRB.INTEGER, name=f"s{i}")
    model.update()

    # Constraints: coverage for each day
    for d in range(n_days):
        coverage = gp.quicksum(s[(d - k) % n_days] for k in range(work_days_consecutive))
        model.addConstr(coverage >= need[d], name=f"cover_day_{d}")

    # Objective: minimize total workers started
    model.setObjective(gp.quicksum(s[i] for i in range(n_days)), GRB.MINIMIZE)
    model.update()

    variables = {f"s{i}": s[i] for i in range(n_days)}
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.CUTOFF: "CUTOFF",
    }
    status_str = status_map.get(status, str(status))

    objective = model.ObjVal

    solution = {f"s{i}": variables[f"s{i}"].X for i in range(len(variables))}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }