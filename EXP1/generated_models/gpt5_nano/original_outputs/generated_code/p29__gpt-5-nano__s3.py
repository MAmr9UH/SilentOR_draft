import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create flat binary decision variables x_Worker_Task
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            v = m.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = v

    m.update()

    # Constraint: each task is assigned to exactly one worker
    for t in tasks:
        m.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1,
                    name=f"Task_{t}")

    # Constraint: each worker is assigned to at most one task
    for w in workers:
        m.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1,
                    name=f"Worker_{w}")

    # Objective: minimize total hours
    obj = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    m.setObjective(obj, GRB.MINIMIZE)

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }