import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {}
    
    for worker in data["workers"]:
        for task in data["tasks"]:
            var_name = f"x_{worker}_{task}"
            variables[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
            
    # Each task must be assigned to exactly one worker
    for task in data["tasks"]:
        model.addConstr(gp.quicksum(variables[f"x_{worker}_{task}"] for worker in data["workers"]) == 1, f"one_worker_per_task_{task}")
        
    # Each worker can be assigned to at most one task
    for worker in data["workers"]:
        model.addConstr(gp.quicksum(variables[f"x_{worker}_{task}"] for task in data["tasks"]) <= 1, f"at_most_one_task_per_worker_{worker}")
        
    # Objective: minimize total working hours
    objective = gp.quicksum(data["hours"][worker][task] * variables[f"x_{worker}_{task}"] for worker in data["workers"] for task in data["tasks"])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
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
    
    solution = {var_name: variables[var_name].X for var_name in variables}
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }