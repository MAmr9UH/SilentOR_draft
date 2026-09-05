import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]

    # Create binary decision variables x_w_t
    variables = {}
    for w in workers:
        for t in tasks:
            key = f"x_{w}_{t}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    model.update()

    # Each task is assigned to exactly one worker
    for t in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for w in workers) == 1, name=f"Task_{t}")

    # Each worker is assigned to at most one task
    for w in workers:
        model.addConstr(gp.quicksum(variables[f"x_{w}_{t}"] for t in tasks) <= 1, name=f"Worker_{w}")

    # Objective: minimize total hours
    model.setObjective(gp.quicksum(hours[w][t] * variables[f"x_{w}_{t}"] for w in workers for t in tasks), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Read status and objective
    status_code = model.Status
    obj_val = model.ObjVal if model.Status == GRB.OPTIMAL or model.Status == GRB.FEASIBLE or model.Status == GRB.TIME_LIMIT else None

    # Map status code to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.FEASIBLE: "FEASIBLE",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }
    status_str = status_map.get(status_code, str(status_code))

    # Build solution dictionary with variable values (rounded to 0/1)
    model.update()
    solution = {}
    for w in data["workers"]:
        for t in data["tasks"]:
            key = f"x_{w}_{t}"
            val = variables[key].X
            solution[key] = int(round(float(val)))  # 0 or 1

    result = {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": solution
    }
    return result