from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    m = Model()
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create flat binary decision variables x_W_T
    x = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            v = m.addVar(vtype=GRB.BINARY, name=key)
            x[key] = v

    m.update()

    # Objective: minimize total hours
    obj = quicksum(hours[w][t] * x[f"x_{w}_{t}"] for w in workers for t in tasks)
    m.setObjective(obj, GRB.MINIMIZE)

    # Constraint: each task is assigned to exactly one worker
    for t in tasks:
        m.addConstr(quicksum(x[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Constraint: each worker is assigned to at most one task
    for w in workers:
        m.addConstr(quicksum(x[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    variables = {"variables_keys": x, "note": "Use flat binary variables x_Worker_Task."}
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    model.update()
    status_str = status_map.get(model.Status, str(model.Status))

    obj_val = model.ObjVal if model.ObjVal is not None else 0.0

    solution = {}
    for key, var in variables["variables_keys"].items():
        solution[key] = var.X

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }