import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Silence solver output (optional but helps for clean runs)
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create flat binary decision variables x_Worker_Task
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            v = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize total hours
    obj = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraint: each task must be assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Constraint: each worker can be assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
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

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None
    model.update()

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }