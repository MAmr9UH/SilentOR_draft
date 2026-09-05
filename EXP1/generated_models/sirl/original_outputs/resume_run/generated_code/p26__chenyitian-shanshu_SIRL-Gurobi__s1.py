import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("lab_schedule_model")
    
    variables = {
        "h_1_Mon": model.addVar(name="h_1_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_1_Tue": model.addVar(name="h_1_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_1_Wed": model.addVar(name="h_1_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_1_Thu": model.addVar(name="h_1_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_1_Fri": model.addVar(name="h_1_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "h_2_Mon": model.addVar(name="h_2_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_2_Tue": model.addVar(name="h_2_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_2_Wed": model.addVar(name="h_2_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_2_Thu": model.addVar(name="h_2_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_2_Fri": model.addVar(name="h_2_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "h_3_Mon": model.addVar(name="h_3_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_3_Tue": model.addVar(name="h_3_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_3_Wed": model.addVar(name="h_3_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_3_Thu": model.addVar(name="h_3_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_3_Fri": model.addVar(name="h_3_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "h_4_Mon": model.addVar(name="h_4_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_4_Tue": model.addVar(name="h_4_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_4_Wed": model.addVar(name="h_4_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_4_Thu": model.addVar(name="h_4_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_4_Fri": model.addVar(name="h_4_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "h_5_Mon": model.addVar(name="h_5_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_5_Tue": model.addVar(name="h_5_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_5_Wed": model.addVar(name="h_5_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_5_Thu": model.addVar(name="h_5_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_5_Fri": model.addVar(name="h_5_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "h_6_Mon": model.addVar(name="h_6_Mon", vtype=GRB.CONTINUOUS, lb=0),
        "h_6_Tue": model.addVar(name="h_6_Tue", vtype=GRB.CONTINUOUS, lb=0),
        "h_6_Wed": model.addVar(name="h_6_Wed", vtype=GRB.CONTINUOUS, lb=0),
        "h_6_Thu": model.addVar(name="h_6_Thu", vtype=GRB.CONTINUOUS, lb=0),
        "h_6_Fri": model.addVar(name="h_6_Fri", vtype=GRB.CONTINUOUS, lb=0),
        "y_1_Mon": model.addVar(name="y_1_Mon", vtype=GRB.BINARY),
        "y_1_Tue": model.addVar(name="y_1_Tue", vtype=GRB.BINARY),
        "y_1_Wed": model.addVar(name="y_1_Wed", vtype=GRB.BINARY),
        "y_1_Thu": model.addVar(name="y_1_Thu", vtype=GRB.BINARY),
        "y_1_Fri": model.addVar(name="y_1_Fri", vtype=GRB.BINARY),
        "y_2_Mon": model.addVar(name="y_2_Mon", vtype=GRB.BINARY),
        "y_2_Tue": model.addVar(name="y_2_Tue", vtype=GRB.BINARY),
        "y_2_Wed": model.addVar(name="y_2_Wed", vtype=GRB.BINARY),
        "y_2_Thu": model.addVar(name="y_2_Thu", vtype=GRB.BINARY),
        "y_2_Fri": model.addVar(name="y_2_Fri", vtype=GRB.BINARY),
        "y_3_Mon": model.addVar(name="y_3_Mon", vtype=GRB.BINARY),
        "y_3_Tue": model.addVar(name="y_3_Tue", vtype=GRB.BINARY),
        "y_3_Wed": model.addVar(name="y_3_Wed", vtype=GRB.BINARY),
        "y_3_Thu": model.addVar(name="y_3_Thu", vtype=GRB.BINARY),
        "y_3_Fri": model.addVar(name="y_3_Fri", vtype=GRB.BINARY),
        "y_4_Mon": model.addVar(name="y_4_Mon", vtype=GRB.BINARY),
        "y_4_Tue": model.addVar(name="y_4_Tue", vtype=GRB.BINARY),
        "y_4_Wed": model.addVar(name="y_4_Wed", vtype=GRB.BINARY),
        "y_4_Thu": model.addVar(name="y_4_Thu", vtype=GRB.BINARY),
        "y_4_Fri": model.addVar(name="y_4_Fri", vtype=GRB.BINARY),
        "y_5_Mon": model.addVar(name="y_5_Mon", vtype=GRB.BINARY),
        "y_5_Tue": model.addVar(name="y_5_Tue", vtype=GRB.BINARY),
        "y_5_Wed": model.addVar(name="y_5_Wed", vtype=GRB.BINARY),
        "y_5_Thu": model.addVar(name="y_5_Thu", vtype=GRB.BINARY),
        "y_5_Fri": model.addVar(name="y_5_Fri", vtype=GRB.BINARY),
        "y_6_Mon": model.addVar(name="y_6_Mon", vtype=GRB.BINARY),
        "y_6_Tue": model.addVar(name="y_6_Tue", vtype=GRB.BINARY),
        "y_6_Wed": model.addVar(name="y_6_Wed", vtype=GRB.BINARY),
        "y_6_Thu": model.addVar(name="y_6_Thu", vtype=GRB.BINARY),
        "y_6_Fri": model.addVar(name="y_6_Fri", vtype=GRB.BINARY)
    }
    
    # Objective function: Minimize gross pay
    model.setObjective(
        gp.quicksum(data["wage"][str(student)] * variables[f"h_{student}_{day}"] for student in data["students"] for day in data["days"]),
        GRB.MINIMIZE)

    # Each day, exactly one student is on duty
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for student in data["undergraduates"] + data["graduates"]) == 1)

    # Maximum duty hours for each student based on availability
    for student in data["students"]:
        for day in data["days"]:
            model.addConstr(variables[f"h_{student}_{day}"] <= data["availability_hours"][str(student)][day])

    # Each undergraduate must work at least 8 hours per week
    for student in data["undergraduates"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for day in data["days"]) >= 8)

    # Each graduate must work at least 7 hours per week
    for student in data["graduates"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for day in data["days"]) >= 7)

    # Each student can work no more than 2 shifts per week
    for student in data["students"]:
        model.addConstr(gp.quicksum(variables[f"y_{student}_{day}"] for day in data["days"]) <= 2)

    # No more than 3 students can be scheduled for duty each day
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables[f"y_{student}_{day}"] for student in data["students"]) <= 3)

    # Linking duty hours and shift variables
    for student in data["students"]:
        for day in data["days"]:
            model.addConstr(variables[f"h_{student}_{day}"] <= 14 * variables[f"y_{student}_{day}"])

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "h_1_Mon": variables["h_1_Mon"].x,
                "h_1_Tue": variables["h_1_Tue"].x,
                "h_1_Wed": variables["h_1_Wed"].x,
                "h_1_Thu": variables["h_1_Thu"].x,
                "h_1_Fri": variables["h_1_Fri"].x,
                "h_2_Mon": variables["h_2_Mon"].x,
                "h_2_Tue": variables["h_2_Tue"].x,
                "h_2_Wed": variables["h_2_Wed"].x,
                "h_2_Thu": variables["h_2_Thu"].x,
                "h_2_Fri": variables["h_2_Fri"].x,
                "h_3_Mon": variables["h_3_Mon"].x,
                "h_3_Tue": variables["h_3_Tue"].x,
                "h_3_Wed": variables["h_3_Wed"].x,
                "h_3_Thu": variables["h_3_Thu"].x,
                "h_3_Fri": variables["h_3_Fri"].x,
                "h_4_Mon": variables["h_4_Mon"].x,
                "h_4_Tue": variables["h_4_Tue"].x,
                "h_4_Wed": variables["h_4_Wed"].x,
                "h_4_Thu": variables["h_4_Thu"].x,
                "h_4_Fri": variables["h_4_Fri"].x,
                "h_5_Mon": variables["h_5_Mon"].x,
                "h_5_Tue": variables["h_5_Tue"].x,
                "h_5_Wed": variables["h_5_Wed"].x,
                "h_5_Thu": variables["h_5_Thu"].x,
                "h_5_Fri": variables["h_5_Fri"].x,
                "h_6_Mon": variables["h_6_Mon"].x,
                "h_6_Tue": variables["h_6_Tue"].x,
                "h_6_Wed": variables["h_6_Wed"].x,
                "h_6_Thu": variables["h_6_Thu"].x,
                "h_6_Fri": variables["h_6_Fri"].x,
                "y_1_Mon": variables["y_1_Mon"].x,
                "y_1_Tue": variables["y_1_Tue"].x,
                "y_1_Wed": variables["y_1_Wed"].x,
                "y_1_Thu": variables["y_1_Thu"].x,
                "y_1_Fri": variables["y_1_Fri"].x,
                "y_2_Mon": variables["y_2_Mon"].x,
                "y_2_Tue": variables["y_2_Tue"].x,
                "y_2_Wed": variables["y_2_Wed"].x,
                "y_2_Thu": variables["y_2_Thu"].x,
                "y_2_Fri": variables["y_2_Fri"].x,
                "y_3_Mon": variables["y_3_Mon"].x,
                "y_3_Tue": variables["y_3_Tue"].x,
                "y_3_Wed": variables["y_3_Wed"].x,
                "y_3_Thu": variables["y_3_Thu"].x,
                "y_3_Fri": variables["y_3_Fri"].x,
                "y_4_Mon": variables["y_4_Mon"].x,
                "y_4_Tue": variables["y_4_Tue"].x,
                "y_4_Wed": variables["y_4_Wed"].x,
                "y_4_Thu": variables["y_4_Thu"].x,
                "y_4_Fri": variables["y_4_Fri"].x,
                "y_5_Mon": variables["y_5_Mon"].x,
                "y_5_Tue": variables["y_5_Tue"].x,
                "y_5_Wed": variables["y_5_Wed"].x,
                "y_5_Thu": variables["y_5_Thu"].x,
                "y_5_Fri": variables["y_5_Fri"].x,
                "y_6_Mon": variables["y_6_Mon"].x,
                "y_6_Tue": variables["y_6_Tue"].x,
                "y_6_Wed": variables["y_6_Wed"].x,
                "y_6_Thu": variables["y_6_Thu"].x,
                "y_6_Fri": variables["y_6_Fri"].x
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "h_1_Mon": None,
                "h_1_Tue": None,
                "h_1_Wed": None,
                "h_1_Thu": None,
                "h_1_Fri": None,
                "h_2_Mon": None,
                "h_2_Tue": None,
                "h_2_Wed": None,
                "h_2_Thu": None,
                "h_2_Fri": None,
                "h_3_Mon": None,
                "h_3_Tue": None,
                "h_3_Wed": None,
                "h_3_Thu": None,
                "h_3_Fri": None,
                "h_4_Mon": None,
                "h_4_Tue": None,
                "h_4_Wed": None,
                "h_4_Thu": None,
                "h_4_Fri": None,
                "h_5_Mon": None,
                "h_5_Tue": None,
                "h_5_Wed": None,
                "h_5_Thu": None,
                "h_5_Fri": None,
                "h_6_Mon": None,
                "h_6_Tue": None,
                "h_6_Wed": None,
                "h_6_Thu": None,
                "h_6_Fri": None,
                "y_1_Mon": None,
                "y_1_Tue": None,
                "y_1_Wed": None,
                "y_1_Thu": None,
                "y_1_Fri": None,
                "y_2_Mon": None,
                "y_2_Tue": None,
                "y_2_Wed": None,
                "y_2_Thu": None,
                "y_2_Fri": None,
                "y_3_Mon": None,
                "y_3_Tue": None,
                "y_3_Wed": None,
                "y_3_Thu": None,
                "y_3_Fri": None,
                "y_4_Mon": None,
                "y_4_Tue": None,
                "y_4_Wed": None,
                "y_4_Thu": None,
                "y_4_Fri": None,
                "y_5_Mon": None,
                "y_5_Tue": None,
                "y_5_Wed": None,
                "y_5_Thu": None,
                "y_5_Fri": None,
                "y_6_Mon": None,
                "y_6_Tue": None,
                "y_6_Wed": None,
                "y_6_Thu": None,
                "y_6_Fri": None
            }
        }

    return solution