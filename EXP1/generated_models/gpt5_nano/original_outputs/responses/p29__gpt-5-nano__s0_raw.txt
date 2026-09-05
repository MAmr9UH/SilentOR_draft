import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model and a dict of decision variables.

    Variables are flat binary x_W_T indicating worker W is assigned to task T.
    """
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    model = gp.Model()
    model.Params.OutputFlag = 0  # silent
    # Create variables
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    model.update()

    # Constraint: each task must be assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Constraint: each worker can be assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    # Objective: minimize total hours
    objective = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
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
    else:
        status_str = str(status_code)

    # Read objective
    obj_val = float(model.ObjVal)

    # Read variable values
    model.update()
    solution = {}
    for w in data["workers"]:
        for t in data["tasks"]:
            key = f"x_{w}_{t}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }