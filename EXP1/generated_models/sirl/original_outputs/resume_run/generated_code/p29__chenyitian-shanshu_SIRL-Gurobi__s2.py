import gurobipy as gp
from gurobipy import GRB
import json

def build_model(data: dict) -> tuple:
    model = gp.Model("worker_task_assignment")
    
    workers = data["workers"]
    tasks = data["tasks"]
    hours = data["hours"]
    
    variables = {}
    
    for worker in workers:
        for task in tasks:
            variables[f"x_{worker}_{task}"] = model.addVar(name=f"x_{worker}_{task}", vtype=GRB.BINARY)

    # Objective function: Minimize total working hours
    model.setObjective(gp.quicksum(hours[worker][task] * variables[f"x_{worker}_{task}"] for worker in workers for task in tasks), GRB.MINIMIZE)

    # Each task is assigned to exactly one worker
    for task in tasks:
        model.addConstr(gp.quicksum(variables[f"x_{worker}_{task}"] for worker in workers) == 1)

    # Exactly 4 workers are selected
    model.addConstr(gp.quicksum(variables[f"x_{worker}_{task}"] for worker in workers for task in tasks) == 4)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "x_I_A": variables["x_I_A"].x,
                "x_I_B": variables["x_I_B"].x,
                "x_I_C": variables["x_I_C"].x,
                "x_I_D": variables["x_I_D"].x,
                "x_II_A": variables["x_II_A"].x,
                "x_II_B": variables["x_II_B"].x,
                "x_II_C": variables["x_II_C"].x,
                "x_II_D": variables["x_II_D"].x,
                "x_III_A": variables["x_III_A"].x,
                "x_III_B": variables["x_III_B"].x,
                "x_III_C": variables["x_III_C"].x,
                "x_III_D": variables["x_III_D"].x,
                "x_IV_A": variables["x_IV_A"].x,
                "x_IV_B": variables["x_IV_B"].x,
                "x_IV_C": variables["x_IV_C"].x,
                "x_IV_D": variables["x_IV_D"].x,
                "x_V_A": variables["x_V_A"].x,
                "x_V_B": variables["x_V_B"].x,
                "x_V_C": variables["x_V_C"].x,
                "x_V_D": variables["x_V_D"].x
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "x_I_A": 0,
                "x_I_B": 0,
                "x_I_C": 0,
                "x_I_D": 0,
                "x_II_A": 0,
                "x_II_B": 0,
                "x_II_C": 0,
                "x_II_D": 0,
                "x_III_A": 0,
                "x_III_B": 0,
                "x_III_C": 0,
                "x_III_D": 0,
                "x_IV_A": 0,
                "x_IV_B": 0,
                "x_IV_C": 0,
                "x_IV_D": 0,
                "x_V_A": 0,
                "x_V_B": 0,
                "x_V_C": 0,
                "x_V_D": 0
            }
        }

    return solution