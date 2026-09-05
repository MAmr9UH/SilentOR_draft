def build_model(data: dict):
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model()
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create decision variables: x_W_T for each worker W and task T
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    model.update()

    # Each task must be assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Assign_{t}")

    # Each worker can be assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    # Objective: minimize total hours
    objective = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    model.setObjective(objective, GRB.MINIMIZE)

    return model, variables

def solve(data: dict):
    import gurobipy as gp

    model, variables = build_model(data)
    model.optimize()

    # Map status to string
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
    elif status_code == gp.GRB.CUTOFF:
        status_str = "CUTOFF"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for key in variables:
        solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }