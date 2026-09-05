import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_staffing_model")
    
    # Define demand for each day
    demand = data["demand"]
    
    # Initialize decision variables
    variables = {
        "start_Monday": model.addVar(name="start_Monday", vtype=GRB.INTEGER, lb=0),
        "start_Tuesday": model.addVar(name="start_Tuesday", vtype=GRB.INTEGER, lb=0),
        "start_Wednesday": model.addVar(name="start_Wednesday", vtype=GRB.INTEGER, lb=0),
        "start_Thursday": model.addVar(name="start_Thursday", vtype=GRB.INTEGER, lb=0),
        "start_Friday": model.addVar(name="start_Friday", vtype=GRB.INTEGER, lb=0),
        "start_Saturday": model.addVar(name="start_Saturday", vtype=GRB.INTEGER, lb=0),
        "start_Sunday": model.addVar(name="start_Sunday", vtype=GRB.INTEGER, lb=0)
    }
    
    # Objective function: Minimize the total number of workers
    model.setObjective(
        variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] +
        variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] +
        variables["start_Sunday"],
        GRB.MINIMIZE)
    
    # Constraints for each day
    for day in data["days"]:
        if day == "Monday":
            model.addConstr(variables["start_Monday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Monday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Monday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Monday"] + variables["start_Sunday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
            model.addConstr(variables["start_Sunday"] >= 0)
        
        elif day == "Tuesday":
            model.addConstr(variables["start_Tuesday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
            model.addConstr(variables["start_Saturday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
        
        elif day == "Wednesday":
            model.addConstr(variables["start_Wednesday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
            model.addConstr(variables["start_Saturday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
        
        elif day == "Thursday":
            model.addConstr(variables["start_Thursday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
            model.addConstr(variables["start_Saturday"] >= 0)
        
        elif day == "Friday":
            model.addConstr(variables["start_Friday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
            model.addConstr(variables["start_Saturday"] >= 0)
        
        elif day == "Saturday":
            model.addConstr(variables["start_Saturday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
        
        elif day == "Sunday":
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] >= 0)
            model.addConstr(variables["start_Sunday"] >= 0)
            model.addConstr(variables["start_Monday"] >= 0)
            model.addConstr(variables["start_Tuesday"] >= 0)
            model.addConstr(variables["start_Wednesday"] >= 0)
            model.addConstr(variables["start_Thursday"] >= 0)
            model.addConstr(variables["start_Friday"] >= 0)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "start_Monday": variables["start_Monday"].x,
            "start_Tuesday": variables["start_Tuesday"].x,
            "start_Wednesday": variables["start_Wednesday"].x,
            "start_Thursday": variables["start_Thursday"].x,
            "start_Friday": variables["start_Friday"].x,
            "start_Saturday": variables["start_Saturday"].x,
            "start_Sunday": variables["start_Sunday"].x
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