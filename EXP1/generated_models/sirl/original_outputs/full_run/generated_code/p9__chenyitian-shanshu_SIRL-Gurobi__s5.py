import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_hiring_model")
    
    # Number of days
    days = data["days"]
    
    # Employees needed each day
    employees_needed = data["employees_needed"]
    
    # Work days consecutive
    work_days_consecutive = data["work_days_consecutive"]
    
    # Initialize decision variables
    variables = {}
    for day in days:
        variables[day] = model.addVar(name=f"s{days.index(day)}", vtype=GRB.INTEGER, lb=0)
    
    # Objective function: Minimize total number of employees
    model.setObjective(gp.quicksum(variables[day] for day in days), GRB.MINIMIZE)
    
    # Constraint: Number of employees working each day
    for day in days:
        model.addConstr(
            variables[day] +
            variables[(days[(days.index(day) + 1) % 7])] +
            variables[(days[(days.index(day) + 2) % 7])] +
            variables[(days[(days.index(day) + 3) % 7])] +
            variables[(days[(days.index(day) + 4) % 7])] -
            employees_needed[days.index(day)] <= 0
        )
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    
    # Solve the model
    model.optimize()
    
    # Check if the model is optimal
    if model.status == GRB.OPTIMAL:
        solution = {
            "s0": variables["Mon"].x,
            "s1": variables["Tue"].x,
            "s2": variables["Wed"].x,
            "s3": variables["Thu"].x,
            "s4": variables["Fri"].x,
            "s5": variables["Sat"].x,
            "s6": variables["Sun"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }