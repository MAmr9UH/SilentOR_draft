import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create flat binary decision variables: x_W_T
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    model.update()

    # Objective: minimize total hours
    model.setObjective(
        gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks),
        GRB.MINIMIZE
    )

    # Constraint: each task must be assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Constraint: each worker is assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.FEASIBLE: "FEASIBLE",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status_str = status_map.get(status_code, str(status_code))

    solution = {}
    for w in data["workers"]:
        for t in data["tasks"]:
            key = f"x_{w}_{t}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }