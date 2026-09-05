import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("post_office_staffing_model")
    
    # Define demand for each day
    demand = data["demand"]
    
    # Initialize decision variables
    start_Monday = model.addVar(name="start_Monday", vtype=GRB.INTEGER, lb=0)
    start_Tuesday = model.addVar(name="start_Tuesday", vtype=GRB.INTEGER, lb=0)
    start_Wednesday = model.addVar(name="start_Wednesday", vtype=GRB.INTEGER, lb=0)
    start_Thursday = model.addVar(name="start_Thursday", vtype=GRB.INTEGER, lb=0)
    start_Friday = model.addVar(name="start_Friday", vtype=GRB.INTEGER, lb=0)
    start_Saturday = model.addVar(name="start_Saturday", vtype=GRB.INTEGER, lb=0)
    start_Sunday = model.addVar(name="start_Sunday", vtype=GRB.INTEGER, lb=0)
    
    variables = {
        "start_Monday": start_Monday,
        "start_Tuesday": start_Tuesday,
        "start_Wednesday": start_Wednesday,
        "start_Thursday": start_Thursday,
        "start_Friday": start_Friday,
        "start_Saturday": start_Saturday,
        "start_Sunday": start_Sunday
    }
    
    # Define the demand for each day
    for day in data["days"]:
        if day == "Monday":
            model.addConstr(start_Monday + start_Tuesday + start_Wednesday + start_Thursday + start_Friday >= demand[day])
            model.addConstr(start_Saturday + start_Sunday + start_Monday >= demand[day])
        elif day == "Tuesday":
            model.addConstr(start_Tuesday + start_Wednesday + start_Thursday + start_Friday + start_Saturday >= demand[day])
            model.addConstr(start_Sunday + start_Monday + start_Tuesday >= demand[day])
        elif day == "Wednesday":
            model.addConstr(start_Wednesday + start_Thursday + start_Friday + start_Saturday + start_Sunday >= demand[day])
            model.addConstr(start_Monday + start_Tuesday + start_Wednesday >= demand[day])
        elif day == "Thursday":
            model.addConstr(start_Thursday + start_Friday + start_Saturday + start_Sunday + start_Monday >= demand[day])
            model.addConstr(start_Tuesday + start_Wednesday + start_Thursday >= demand[day])
        elif day == "Friday":
            model.addConstr(start_Friday + start_Saturday + start_Sunday + start_Monday + start_Tuesday >= demand[day])
            model.addConstr(start_Wednesday + start_Thursday + start_Friday >= demand[day])
        elif day == "Saturday":
            model.addConstr(start_Saturday + start_Sunday + start_Monday + start_Tuesday + start_Wednesday >= demand[day])
            model.addConstr(start_Thursday + start_Friday + start_Saturday >= demand[day])
        elif day == "Sunday":
            model.addConstr(start_Sunday + start_Monday + start_Tuesday + start_Wednesday + start_Thursday >= demand[day])
            model.addConstr(start_Friday + start_Saturday + start_Sunday >= demand[day])
    
    # Objective function: Minimize the total number of workers
    model.setObjective(start_Monday + start_Tuesday + start_Wednesday + start_Thursday + start_Friday + start_Saturday + start_Sunday, GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    
    # Solve the model
    model.optimize()
    
    # Check if the model is optimal
    if model.status == GRB.OPTIMAL:
        solution = {
            "start_Monday": variables["start_Monday"].x,
            "start_Tuesday": variables["start_Tuesday"].x,
            "start_Wednesday": variables["start_Wednesday"].x,
            "start_Thursday": variables["start_Thursday"].x,
            "start_Friday": variables["start_Friday"].x,
            "start_Saturday": variables["start_Saturday"].x,
            "start_Sunday": variables["start_Sunday"].x,
            "objective": model.objVal
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