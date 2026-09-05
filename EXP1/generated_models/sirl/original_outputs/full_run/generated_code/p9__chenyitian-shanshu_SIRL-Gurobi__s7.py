import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_hiring_model")
    
    # Initialize decision variables
    variables = {
        "s0": {},
        "s1": {},
        "s2": {},
        "s3": {},
        "s4": {},
        "s5": {},
        "s6": {}
    }
    
    # Number of employees needed each day
    employees_needed = data["employees_needed"]
    
    # Days of the week
    days = data["days"]
    
    # Work days consecutive
    work_days_consecutive = data["work_days_consecutive"]
    
    # Define decision variables
    for day in days:
        variables[day] = model.addVar(name=f"s_{days.index(day)}", vtype=GRB.INTEGER, lb=0)
    
    # Constraint: Number of employees needed each day
    for day in days:
        model.addConstr(
            variables["s0"][(day == "Mon")] +
            variables["s1"][(day == "Tue")] +
            variables["s2"][(day == "Wed")] +
            variables["s3"][(day == "Thu")] +
            variables["s4"][(day == "Fri")] +
            variables["s5"][(day == "Sat")] +
            variables["s6"][(day == "Sun")] >= employees_needed[days.index(day)]
        )
    
        if day == "Mon":
            model.addConstr(
                variables["s0"] + 
                variables["s1"] + 
                variables["s2"] + 
                variables["s3"] + 
                variables["s4"] + 
                variables["s5"] + 
                variables["s6"] <= 7 * GRB.INFINITY
            )
        elif day == "Tue":
            model.addConstr(
                variables["s1"] + 
                variables["s2"] + 
                variables["s3"] + 
                variables["s4"] + 
                variables["s5"] + 
                variables["s6"] + 
                variables["s0"] <= 7 * GRB.INFINITY
            )
        elif day == "Wed":
            model.addConstr(
                variables["s2"] + 
                variables["s3"] + 
                variables["s4"] + 
                variables["s5"] + 
                variables["s6"] + 
                variables["s0"] + 
                variables["s1"] <= 7 * GRB.INFINITY
            )
        elif day == "Thu":
            model.addConstr(
                variables["s3"] + 
                variables["s4"] + 
                variables["s5"] + 
                variables["s6"] + 
                variables["s0"] + 
                variables["s1"] + 
                variables["s2"] <= 7 * GRB.INFINITY
            )
        elif day == "Fri":
            model.addConstr(
                variables["s4"] + 
                variables["s5"] + 
                variables["s6"] + 
                variables["s0"] + 
                variables["s1"] + 
                variables["s2"] + 
                variables["s3"] <= 7 * GRB.INFINITY
            )
        elif day == "Sat":
            model.addConstr(
                variables["s5"] + 
                variables["s6"] + 
                variables["s0"] + 
                variables["s1"] + 
                variables["s2"] + 
                variables["s3"] + 
                variables["s4"] <= 7 * GRB.INFINITY
            )
        elif day == "Sun":
            model.addConstr(
                variables["s6"] + 
                variables["s0"] + 
                variables["s1"] + 
                variables["s2"] + 
                variables["s3"] + 
                variables["s4"] + 
                variables["s5"] <= 7 * GRB.INFINITY
            )
    
    # Objective function: Minimize the total number of employees
    model.setObjective(
        variables["s0"] + 
        variables["s1"] + 
        variables["s2"] + 
        variables["s3"] + 
        variables["s4"] + 
        variables["s5"] + 
        variables["s6"],
        GRB.MINIMIZE
    )
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "s0": variables["s0"].x,
            "s1": variables["s1"].x,
            "s2": variables["s2"].x,
            "s3": variables["s3"].x,
            "s4": variables["s4"].x,
            "s5": variables["s5"].x,
            "s6": variables["s6"].x,
            "objective": model.objVal
        }
        return {"status": "OPTIMAL", "objective": model.objVal, "solution": solution}
    else:
        return {"status": "INFEASIBLE", "objective": None, "solution": None}