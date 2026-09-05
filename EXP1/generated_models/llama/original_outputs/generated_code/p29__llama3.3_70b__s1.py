import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {}
    
    for worker in data["workers"]:
        for task in data["tasks"]:
            var_name = f"x_{worker}_{task}"
            variables[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Objective function
    obj_expr = gp.quicksum(variables[f"x_{worker}_{task}"] * data["hours"][worker][task] for worker in data["workers"] for task in data["tasks"])
    model.setObjective(obj_expr, gp.GRB.MINIMIZE)
    
    # Constraints: each task is assigned to exactly one worker
    for task in data["tasks"]:
        task_constraint = gp.quicksum(variables[f"x_{worker}_{task}"] for worker in data["workers"])
        model.addConstr(task_constraint == 1, f"Task_{task}_constraint")
    
    # Constraints: each worker is assigned to at most one task
    for worker in data["workers"]:
        worker_constraint = gp.quicksum(variables[f"x_{worker}_{task}"] for task in data["tasks"])
        model.addConstr(worker_constraint <= 1, f"Worker_{worker}_constraint")
    
    # Constraints: exactly four workers are assigned to tasks
    total_workers_assigned = gp.quicksum(variables[var_name] for var_name in variables)
    model.addConstr(total_workers_assigned == 4, "Total_workers_assigned_constraint")
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {}
    for var_name in _:
        solution[var_name] = _.get(var_name).X
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }