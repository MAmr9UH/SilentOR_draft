def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    m = gp.Model()

    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Decision variables: binary x_w_t
    x = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            x[key] = m.addVar(vtype=GRB.BINARY, name=key)

    m.update()

    # Each task must be assigned to exactly one worker
    for t in tasks:
        m.addConstr(gp.quicksum(x[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Each worker can be assigned to at most one task
    for w in workers:
        m.addConstr(gp.quicksum(x[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    # Objective: minimize total hours
    obj = gp.quicksum(hours[w][t] * x[f"x_{w}_{t}"] for w in workers for t in tasks)
    m.setObjective(obj, GRB.MINIMIZE)

    return m, x

def solve(data: dict) -> dict:
    import gurobipy as gp

    model, variables = build_model(data)
    model.optimize()

    # Map status to a human-readable string
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    model.update()
    objective = float(model.ObjVal)

    # Build solution dictionary with all x_w_t values
    solution = {}
    for w in data["workers"]:
        for t in data["tasks"]:
            key = f"x_{w}_{t}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }