import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_hiring_model")
    
    # Number of days
    days = data["days"]
    
    # Employees needed each day
    employees_needed = data["employees_needed"]
    
    # Number of consecutive work days
    work_days_consecutive = data["work_days_consecutive"]
    
    # Initialize decision variables
    variables = {}
    for day in days:
        variables[day] = model.addVar(name=f"s{days.index(day)}", vtype=GRB.INTEGER, lb=0)
    
    # Objective function: Minimize total number of employees
    model.setObjective(gp.quicksum(variables[day] for day in days), GRB.MINIMIZE)
    
    # Constraint: Number of employees working each day
    for day in days:
        start_days = [days[(days.index(day) + i) % 7] for i in range(work_days_consecutive)]
        model.addConstr(gp.quicksum(variables[start_day] for start_day in start_days) >= employees_needed[days.index(day)])
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "s0": variables["Mon"].x,
                "s1": variables["Tue"].x,
                "s2": variables["Wed"].x,
                "s3": variables["Thu"].x,
                "s4": variables["Fri"].x,
                "s5": variables["Sat"].x,
                "s6": variables["Sun"].x
            }
        }
        return solution
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "s0": None,
                "s1": None,
                "s2": None,
                "s3": None,
                "s4": None,
                "s5": None,
                "s6": None
            }
        }