import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("course_selection_model")
    
    courses = data["courses"]
    
    variables = {
        "sel_calculus": model.addVar(name="sel_calculus", vtype=GRB.BINARY),
        "sel_or": model.addVar(name="sel_or", vtype=GRB.BINARY),
        "sel_ds": model.addVar(name="sel_ds", vtype=GRB.BINARY),
        "sel_ms": model.addVar(name="sel_ms", vtype=GRB.BINARY),
        "sel_cs": model.addVar(name="sel_cs", vtype=GRB.BINARY),
        "sel_cp": model.addVar(name="sel_cp", vtype=GRB.BINARY),
        "sel_fc": model.addVar(name="sel_fc", vtype=GRB.BINARY)
    }
    
    # Each category must have at least 2 courses
    model.addConstr(variables["sel_calculus"] + variables["sel_or"] + variables["sel_ds"] + variables["sel_ms"] + variables["sel_cs"] + variables["sel_cp"] + variables["sel_fc"] >= 2)
    
    # Math category
    model.addConstr(variables["sel_calculus"] + variables["sel_or"] + variables["sel_ds"] + variables["sel_ms"] >= 2)
    
    # Operations Research category
    model.addConstr(variables["sel_or"] + variables["sel_ds"] + variables["sel_ms"] + variables["sel_fc"] >= 2)
    
    # Computer category
    model.addConstr(variables["sel_ds"] + variables["sel_cs"] + variables["sel_or"] >= 2)
    
    # Prerequisite: computer simulation or data structures must be taken after computer programming
    model.addConstr(variables["sel_cs"] + variables["sel_ds"] >= 1)
    
    # Prerequisite: management statistics must be taken after calculus
    model.addConstr(variables["sel_ms"] + variables["sel_calculus"] >= 1)
    
    # Prerequisite: forecasting must be taken after management statistics
    model.addConstr(variables["sel_fc"] + variables["sel_ms"] >= 1)
    
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
            "sel_ms": variables["sel_ms"].x,
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