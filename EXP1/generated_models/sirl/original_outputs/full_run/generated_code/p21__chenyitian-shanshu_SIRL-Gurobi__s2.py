import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_staffing_model")
    
    # Define decision variables
    variables = {
        "start_Monday": model.addVar(name="start_Monday", vtype=GRB.INTEGER, lb=0),
        "start_Tuesday": model.addVar(name="start_Tuesday", vtype=GRB.INTEGER, lb=0),
        "start_Wednesday": model.addVar(name="start_Wednesday", vtype=GRB.INTEGER, lb=0),
        "start_Thursday": model.addVar(name="start_Thursday", vtype=GRB.INTEGER, lb=0),
        "start_Friday": model.addVar(name="start_Friday", vtype=GRB.INTEGER, lb=0),
        "start_Saturday": model.addVar(name="start_Saturday", vtype=GRB.INTEGER, lb=0),
        "start_Sunday": model.addVar(name="start_Sunday", vtype=GRB.INTEGER, lb=0)
    }
    
    # Demand for each day
    demand = data["demand"]
    
    # Number of work consecutive days and off consecutive days
    work_consecutive_days = data["work_consecutive_days"]
    off_consecutive_days = data["off_consecutive_days"]
    
    # Build constraints
    for day in data["days"]:
        if day == "Monday":
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] >= demand["Tuesday"])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand["Wednesday"])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand["Thursday"])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Friday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Saturday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Tuesday":
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand["Wednesday"])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand["Thursday"])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Friday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Saturday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Wednesday":
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand["Thursday"])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Friday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Saturday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Thursday":
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Friday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Saturday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Friday":
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Saturday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Saturday":
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Sunday":
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand[day])
    
    # Minimize the total number of workers
    model.setObjective(
        variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"],
        GRB.MINIMIZE)
    
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