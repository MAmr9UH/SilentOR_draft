def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    hours = data["hours"]
    workers = data["workers"]
    tasks = data["tasks"]

    model = gp.Model()
    # Optional: suppress solver output
    try:
        model.Params.LogToConsole = 0
    except Exception:
        try:
            model.Params.OutputFlag = 0
        except Exception:
            pass

    # Create decision variables: x_w_t for all worker w and task t
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            v = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = v

    model.update()

    # Each task must be assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Each worker is assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    # Objective: minimize total hours
    objective = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    model.setObjective(objective, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    import gurobipy as gp
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    for key in sorted(variables.keys()):
        solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }