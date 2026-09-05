import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_staffing_model")
    
    variables = {
        "start_Monday": {},
        "start_Tuesday": {},
        "start_Wednesday": {},
        "start_Thursday": {},
        "start_Friday": {},
        "start_Saturday": {},
        "start_Sunday": {}
    }
    
    # Define decision variables
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        variables[day] = model.addVar(name=f"start_{day}", vtype=GRB.INTEGER, lb=0)
    
    # Demand for each day
    demand = data["demand"]
    
    # Build constraints
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if day == "Monday":
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand[day])
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Tuesday"])
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Wednesday"])
            model.addConstr(variables["start_Monday"] + variables["start_Tuesday"] >= demand["Thursday"])
            model.addConstr(variables["start_Monday"] >= demand["Friday"])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand["Saturday"])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Sunday"])
        elif day == "Tuesday":
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] >= demand[day])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand["Wednesday"])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Thursday"])
            model.addConstr(variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Friday"])
            model.addConstr(variables["start_Tuesday"] + variables["start_Saturday"] >= demand["Saturday"])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand["Sunday"])
        elif day == "Wednesday":
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand[day])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] >= demand["Thursday"])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] + variables["start_Friday"] >= demand["Friday"])
            model.addConstr(variables["start_Wednesday"] + variables["start_Thursday"] >= demand["Saturday"])
            model.addConstr(variables["start_Wednesday"] + variables["start_Sunday"] >= demand["Sunday"])
        elif day == "Thursday":
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand[day])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand["Friday"])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] + variables["start_Saturday"] >= demand["Saturday"])
            model.addConstr(variables["start_Thursday"] + variables["start_Friday"] >= demand["Sunday"])
            model.addConstr(variables["start_Thursday"] + variables["start_Monday"] >= demand["Monday"])
        elif day == "Friday":
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand[day])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand["Saturday"])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] + variables["start_Sunday"] >= demand["Sunday"])
            model.addConstr(variables["start_Friday"] + variables["start_Saturday"] >= demand["Monday"])
            model.addConstr(variables["start_Friday"] + variables["start_Monday"] >= demand["Tuesday"])
        elif day == "Saturday":
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand[day])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Sunday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] + variables["start_Monday"] >= demand["Monday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Sunday"] >= demand["Tuesday"])
            model.addConstr(variables["start_Saturday"] + variables["start_Monday"] >= demand["Wednesday"])
        elif day == "Sunday":
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] + variables["start_Thursday"] >= demand[day])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] + variables["start_Wednesday"] >= demand["Monday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] + variables["start_Tuesday"] >= demand["Tuesday"])
            model.addConstr(variables["start_Sunday"] + variables["start_Monday"] >= demand["Wednesday"])
            model.addConstr(variables["start_Sunday"] >= demand["Thursday"])
    
    # Objective function: Minimize the total number of workers
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