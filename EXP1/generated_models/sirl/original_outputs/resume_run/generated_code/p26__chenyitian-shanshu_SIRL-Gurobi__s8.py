import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("lab_schedule_model")
    
    # Initialize decision variables
    variables = {
        "h": {
            "1_Mon": model.addVar(name="h_1_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "1_Tue": model.addVar(name="h_1_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "1_Wed": model.addVar(name="h_1_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "1_Thu": model.addVar(name="h_1_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "1_Fri": model.addVar(name="h_1_Fri", vtype=GRB.CONTINUOUS, lb=0),
            "2_Mon": model.addVar(name="h_2_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "2_Tue": model.addVar(name="h_2_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "2_Wed": model.addVar(name="h_2_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "2_Thu": model.addVar(name="h_2_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "2_Fri": model.addVar(name="h_2_Fri", vtype=GRB.CONTINUOUS, lb=0),
            "3_Mon": model.addVar(name="h_3_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "3_Tue": model.addVar(name="h_3_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "3_Wed": model.addVar(name="h_3_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "3_Thu": model.addVar(name="h_3_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "3_Fri": model.addVar(name="h_3_Fri", vtype=GRB.CONTINUOUS, lb=0),
            "4_Mon": model.addVar(name="h_4_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "4_Tue": model.addVar(name="h_4_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "4_Wed": model.addVar(name="h_4_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "4_Thu": model.addVar(name="h_4_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "4_Fri": model.addVar(name="h_4_Fri", vtype=GRB.CONTINUOUS, lb=0),
            "5_Mon": model.addVar(name="h_5_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "5_Tue": model.addVar(name="h_5_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "5_Wed": model.addVar(name="h_5_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "5_Thu": model.addVar(name="h_5_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "5_Fri": model.addVar(name="h_5_Fri", vtype=GRB.CONTINUOUS, lb=0),
            "6_Mon": model.addVar(name="h_6_Mon", vtype=GRB.CONTINUOUS, lb=0),
            "6_Tue": model.addVar(name="h_6_Tue", vtype=GRB.CONTINUOUS, lb=0),
            "6_Wed": model.addVar(name="h_6_Wed", vtype=GRB.CONTINUOUS, lb=0),
            "6_Thu": model.addVar(name="h_6_Thu", vtype=GRB.CONTINUOUS, lb=0),
            "6_Fri": model.addVar(name="h_6_Fri", vtype=GRB.CONTINUOUS, lb=0)
        },
        "y": {
            "1_Mon": model.addVar(name="y_1_Mon", vtype=GRB.BINARY),
            "1_Tue": model.addVar(name="y_1_Tue", vtype=GRB.BINARY),
            "1_Wed": model.addVar(name="y_1_Wed", vtype=GRB.BINARY),
            "1_Thu": model.addVar(name="y_1_Thu", vtype=GRB.BINARY),
            "1_Fri": model.addVar(name="y_1_Fri", vtype=GRB.BINARY),
            "2_Mon": model.addVar(name="y_2_Mon", vtype=GRB.BINARY),
            "2_Tue": model.addVar(name="y_2_Tue", vtype=GRB.BINARY),
            "2_Wed": model.addVar(name="y_2_Wed", vtype=GRB.BINARY),
            "2_Thu": model.addVar(name="y_2_Thu", vtype=GRB.BINARY),
            "2_Fri": model.addVar(name="y_2_Fri", vtype=GRB.BINARY),
            "3_Mon": model.addVar(name="y_3_Mon", vtype=GRB.BINARY),
            "3_Tue": model.addVar(name="y_3_Tue", vtype=GRB.BINARY),
            "3_Wed": model.addVar(name="y_3_Wed", vtype=GRB.BINARY),
            "3_Thu": model.addVar(name="y_3_Thu", vtype=GRB.BINARY),
            "3_Fri": model.addVar(name="y_3_Fri", vtype=GRB.BINARY),
            "4_Mon": model.addVar(name="y_4_Mon", vtype=GRB.BINARY),
            "4_Tue": model.addVar(name="y_4_Tue", vtype=GRB.BINARY),
            "4_Wed": model.addVar(name="y_4_Wed", vtype=GRB.BINARY),
            "4_Thu": model.addVar(name="y_4_Thu", vtype=GRB.BINARY),
            "4_Fri": model.addVar(name="y_4_Fri", vtype=GRB.BINARY),
            "5_Mon": model.addVar(name="y_5_Mon", vtype=GRB.BINARY),
            "5_Tue": model.addVar(name="y_5_Tue", vtype=GRB.BINARY),
            "5_Wed": model.addVar(name="y_5_Wed", vtype=GRB.BINARY),
            "5_Thu": model.addVar(name="y_5_Thu", vtype=GRB.BINARY),
            "5_Fri": model.addVar(name="y_5_Fri", vtype=GRB.BINARY),
            "6_Mon": model.addVar(name="y_6_Mon", vtype=GRB.BINARY),
            "6_Tue": model.addVar(name="y_6_Tue", vtype=GRB.BINARY),
            "6_Wed": model.addVar(name="y_6_Wed", vtype=GRB.BINARY),
            "6_Thu": model.addVar(name="y_6_Thu", vtype=GRB.BINARY),
            "6_Fri": model.addVar(name="y_6_Fri", vtype=GRB.BINARY)
        }
    }
    
    # Objective function: Minimize gross pay
    wage = data["wage"]
    model.setObjective(
        gp.quicksum(wage[str(student)] * variables["h"][f"{student}_{day}"] for student in data["students"] for day in data["days"]),
        GRB.MINIMIZE
    )
    
    # Each day, exactly one student is on duty
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables["y"][f"{student}_{day}"] for student in data["students"]) == 1)
    
    # Maximum duty hours for each student based on availability
    availability_hours = data["availability_hours"]
    for student in data["students"]:
        for day in data["days"]:
            model.addConstr(variables["h"][f"{student}_{day}"] <= availability_hours[str(student)][day])
    
    # Each undergraduate must work at least 8 hours per week
    undergraduates = data["undergraduates"]
    for student in undergraduates:
        model.addConstr(gp.quicksum(variables["h"][f"{student}_{day}"] for day in data["days"]) >= 8)
    
    # Each graduate must work at least 7 hours per week
    graduates = data["graduates"]
    for student in graduates:
        model.addConstr(gp.quicksum(variables["h"][f"{student}_{day}"] for day in data["days"]) >= 7)
    
    # Each student can work no more than 2 shifts per week
    for student in data["students"]:
        model.addConstr(gp.quicksum(variables["y"][f"{student}_{day}"] for day in data["days"]) <= 2)
    
    # No more than 3 students can be scheduled for duty each day
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables["y"][f"{student}_{day}"] for student in data["students"]) <= 3)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "h_1_Mon": variables["h"]["1_Mon"].x,
                "h_1_Tue": variables["h"]["1_Tue"].x,
                "h_1_Wed": variables["h"]["1_Wed"].x,
                "h_1_Thu": variables["h"]["1_Thu"].x,
                "h_1_Fri": variables["h"]["1_Fri"].x,
                "h_2_Mon": variables["h"]["2_Mon"].x,
                "h_2_Tue": variables["h"]["2_Tue"].x,
                "h_2_Wed": variables["h"]["2_Wed"].x,
                "h_2_Thu": variables["h"]["2_Thu"].x,
                "h_2_Fri": variables["h"]["2_Fri"].x,
                "h_3_Mon": variables["h"]["3_Mon"].x,
                "h_3_Tue": variables["h"]["3_Tue"].x,
                "h_3_Wed": variables["h"]["3_Wed"].x,
                "h_3_Thu": variables["h"]["3_Thu"].x,
                "h_3_Fri": variables["h"]["3_Fri"].x,
                "h_4_Mon": variables["h"]["4_Mon"].x,
                "h_4_Tue": variables["h"]["4_Tue"].x,
                "h_4_Wed": variables["h"]["4_Wed"].x,
                "h_4_Thu": variables["h"]["4_Thu"].x,
                "h_4_Fri": variables["h"]["4_Fri"].x,
                "h_5_Mon": variables["h"]["5_Mon"].x,
                "h_5_Tue": variables["h"]["5_Tue"].x,
                "h_5_Wed": variables["h"]["5_Wed"].x,
                "h_5_Thu": variables["h"]["5_Thu"].x,
                "h_5_Fri": variables["h"]["5_Fri"].x,
                "h_6_Mon": variables["h"]["6_Mon"].x,
                "h_6_Tue": variables["h"]["6_Tue"].x,
                "h_6_Wed": variables["h"]["6_Wed"].x,
                "h_6_Thu": variables["h"]["6_Thu"].x,
                "h_6_Fri": variables["h"]["6_Fri"].x,
                "y_1_Mon": variables["y"]["1_Mon"].x,
                "y_1_Tue": variables["y"]["1_Tue"].x,
                "y_1_Wed": variables["y"]["1_Wed"].x,
                "y_1_Thu": variables["y"]["1_Thu"].x,
                "y_1_Fri": variables["y"]["1_Fri"].x,
                "y_2_Mon": variables["y"]["2_Mon"].x,
                "y_2_Tue": variables["y"]["2_Tue"].x,
                "y_2_Wed": variables["y"]["2_Wed"].x,
                "y_2_Thu": variables["y"]["2_Thu"].x,
                "y_2_Fri": variables["y"]["2_Fri"].x,
                "y_3_Mon": variables["y"]["3_Mon"].x,
                "y_3_Tue": variables["y"]["3_Tue"].x,
                "y_3_Wed": variables["y"]["3_Wed"].x,
                "y_3_Thu": variables["y"]["3_Thu"].x,
                "y_3_Fri": variables["y"]["3_Fri"].x,
                "y_4_Mon": variables["y"]["4_Mon"].x,
                "y_4_Tue": variables["y"]["4_Tue"].x,
                "y_4_Wed": variables["y"]["4_Wed"].x,
                "y_4_Thu": variables["y"]["4_Thu"].x,
                "y_4_Fri": variables["y"]["4_Fri"].x,
                "y_5_Mon": variables["y"]["5_Mon"].x,
                "y_5_Tue": variables["y"]["5_Tue"].x,
                "y_5_Wed": variables["y"]["5_Wed"].x,
                "y_5_Thu": variables["y"]["5_Thu"].x,
                "y_5_Fri": variables["y"]["5_Fri"].x,
                "y_6_Mon": variables["y"]["6_Mon"].x,
                "y_6_Tue": variables["y"]["6_Tue"].x,
                "y_6_Wed": variables["y"]["6_Wed"].x,
                "y_6_Thu": variables["y"]["6_Thu"].x,
                "y_6_Fri": variables["y"]["6_Fri"].x
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {}
        }
    
    return solution