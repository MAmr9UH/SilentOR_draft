import gurobipy as gp

def build_model(data: dict) -> tuple:
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    model = gp.Model()

    # Create flat binary variables x_W_T
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    model.update()

    # Objective: minimize total hours
    obj = gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraint: Each task is assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Constraint: Each worker is assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective_value = float(model.ObjVal)

    solution = {}
    for w in data["workers"]:
        for t in data["tasks"]:
            key = f"x_{w}_{t}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }