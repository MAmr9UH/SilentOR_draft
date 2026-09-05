import gurobipy as gp
from gurobipy import GRB
import json

def build_model(data: dict) -> tuple:
    model = gp.Model("operations_research_major_model")
    
    courses = data["courses"]
    course_names = data["course_names"]
    
    variables = {
        "sel_calculus": model.addVar(name="sel_calculus", vtype=GRB.BINARY),
        "sel_or": model.addVar(name="sel_or", vtype=GRB.BINARY),
        "sel_ds": model.addVar(name="sel_ds", vtype=GRB.BINARY),
        "sel_bs": model.addVar(name="sel_bs", vtype=GRB.BINARY),
        "sel_cs": model.addVar(name="sel_cs", vtype=GRB.BINARY),
        "sel_cp": model.addVar(name="sel_cp", vtype=GRB.BINARY),
        "sel_fc": model.addVar(name="sel_fc", vtype=GRB.BINARY)
    }
    
    # Each course is either taken (1) or not taken (0)
    
    # At least 2 math courses
    model.addConstr(variables["sel_calculus"] + variables["sel_or"] + variables["sel_ds"] + variables["sel_bs"] >= 2)
    
    # At least 2 OR courses
    model.addConstr(variables["sel_or"] + variables["sel_cs"] + variables["sel_fc"] >= 2)
    
    # At least 2 computer courses
    model.addConstr(variables["sel_ds"] + variables["sel_cs"] + variables["sel_cp"] >= 2)
    
    # Calculus fulfills math
    model.addConstr(variables["sel_calculus"] <= 1)
    
    # Operations research fulfills math and OR
    model.addConstr(variables["sel_or"] <= variables["sel_calculus"] + variables["sel_ds"])
    
    # Data structures fulfills computer and math
    model.addConstr(variables["sel_ds"] <= variables["sel_calculus"] + variables["sel_cp"])
    
    # Business statistics fulfills math and OR
    model.addConstr(variables["sel_bs"] <= variables["sel_calculus"] + variables["sel_or"])
    
    # Computer simulation fulfills OR and computer
    model.addConstr(variables["sel_cs"] <= variables["sel_or"] + variables["sel_ds"])
    
    # Introduction to computer programming fulfills computer
    model.addConstr(variables["sel_cp"] <= variables["sel_ds"])
    
    # Business statistics fulfills math and OR
    model.addConstr(variables["sel_bs"] <= variables["sel_calculus"] + variables["sel_or"])
    
    # Forecasting fulfills OR and math
    model.addConstr(variables["sel_fc"] <= variables["sel_or"] + variables["sel_calculus"])
    
    # Calculus is a prerequisite for business statistics
    model.addConstr(variables["sel_bs"] <= variables["sel_calculus"])
    
    # Introduction to computer programming is a prerequisite for computer simulation
    model.addConstr(variables["sel_cs"] <= variables["sel_cp"])
    
    # Introduction to computer programming is a prerequisite for data structures
    model.addConstr(variables["sel_ds"] <= variables["sel_cp"])
    
    # Business statistics is a prerequisite for forecasting
    model.addConstr(variables["sel_fc"] <= variables["sel_bs"])
    
    # Minimize the number of courses
    model.setObjective(gp.quicksum(variables.values()), GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "sel_calculus": variables["sel_calculus"].x,
            "sel_or": variables["sel_or"].x,
            "sel_ds": variables["sel_ds"].x,
            "sel_bs": variables["sel_bs"].x,
            "sel_cs": variables["sel_cs"].x,
            "sel_cp": variables["sel_cp"].x,
            "sel_fc": variables["sel_fc"].x
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