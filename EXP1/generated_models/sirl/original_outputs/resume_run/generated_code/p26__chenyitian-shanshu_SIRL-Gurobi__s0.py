import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("lab_schedule_model")
    
    # Initialize decision variables
    variables = {
        "h": {
            "1_Mon": model.addVar(name="h_1_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "1_Tue": model.addVar(name="h_1_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "1_Wed": model.addVar(name="h_1_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "1_Thu": model.addVar(name="h_1_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "1_Fri": model.addVar(name="h_1_Fri", lb=0, vtype=GRB.CONTINUOUS),
            "2_Mon": model.addVar(name="h_2_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "2_Tue": model.addVar(name="h_2_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "2_Wed": model.addVar(name="h_2_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "2_Thu": model.addVar(name="h_2_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "2_Fri": model.addVar(name="h_2_Fri", lb=0, vtype=GRB.CONTINUOUS),
            "3_Mon": model.addVar(name="h_3_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "3_Tue": model.addVar(name="h_3_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "3_Wed": model.addVar(name="h_3_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "3_Thu": model.addVar(name="h_3_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "3_Fri": model.addVar(name="h_3_Fri", lb=0, vtype=GRB.CONTINUOUS),
            "4_Mon": model.addVar(name="h_4_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "4_Tue": model.addVar(name="h_4_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "4_Wed": model.addVar(name="h_4_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "4_Thu": model.addVar(name="h_4_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "4_Fri": model.addVar(name="h_4_Fri", lb=0, vtype=GRB.CONTINUOUS),
            "5_Mon": model.addVar(name="h_5_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "5_Tue": model.addVar(name="h_5_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "5_Wed": model.addVar(name="h_5_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "5_Thu": model.addVar(name="h_5_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "5_Fri": model.addVar(name="h_5_Fri", lb=0, vtype=GRB.CONTINUOUS),
            "6_Mon": model.addVar(name="h_6_Mon", lb=0, vtype=GRB.CONTINUOUS),
            "6_Tue": model.addVar(name="h_6_Tue", lb=0, vtype=GRB.CONTINUOUS),
            "6_Wed": model.addVar(name="h_6_Wed", lb=0, vtype=GRB.CONTINUOUS),
            "6_Thu": model.addVar(name="h_6_Thu", lb=0, vtype=GRB.CONTINUOUS),
            "6_Fri": model.addVar(name="h_6_Fri", lb=0, vtype=GRB.CONTINUOUS)
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
    
    # Objective function: Minimize total gross pay
    wages = {
        1: 10.0,
        2: 10.0,
        3: 9.9,
        4: 9.8,
        5: 10.8,
        6: 11.3
    }
    
    model.setObjective(
        gp.quicksum(wages[student] * variables["h"][f"{student}_Mon"] for student in [1, 2, 3, 4, 5, 6]) +
        gp.quicksum(wages[student] * variables["h"][f"{student}_Tue"] for student in [1, 2, 3, 4, 5, 6]) +
        gp.quicksum(wages[student] * variables["h"][f"{student}_Wed"] for student in [1, 2, 3, 4, 5, 6]) +
        gp.quicksum(wages[student] * variables["h"][f"{student}_Thu"] for student in [1, 2, 3, 4, 5, 6]) +
        gp.quicksum(wages[student] * variables["h"][f"{student}_Fri"] for student in [1, 2, 3, 4, 5, 6]),
        GRB.MINIMIZE)

    # Each day must have exactly one student on duty
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        model.addConstr(
            variables["h"]["1_" + day] + variables["h"]["2_" + day] + variables["h"]["3_" + day] +
            variables["h"]["4_" + day] + variables["h"]["5_" + day] + variables["h"]["6_" + day] == 14)

    # Undergraduates must work at least 8 hours per week
    for student in [1, 2, 3, 4]:
        model.addConstr(variables["h"]["{}_Mon".format(student)] + variables["h"]["{}_Tue".format(student)] +
                        variables["h"]["{}_Wed".format(student)] + variables["h"]["{}_Thu".format(student)] +
                        variables["h"]["{}_Fri".format(student)] >= 8)

    # Graduates must work at least 7 hours per week
    for student in [5, 6]:
        model.addConstr(variables["h"]["{}_Mon".format(student)] + variables["h"]["{}_Tue".format(student)] +
                        variables["h"]["{}_Wed".format(student)] + variables["h"]["{}_Thu".format(student)] +
                        variables["h"]["{}_Fri".format(student)] >= 7)

    # Each student can work no more than 2 shifts per week
    for student in [1, 2, 3, 4, 5, 6]:
        model.addConstr(variables["y"]["{}_Mon".format(student)] + variables["y"]["{}_Tue".format(student)] +
                        variables["y"]["{}_Wed".format(student)] + variables["y"]["{}_Thu".format(student)] +
                        variables["y"]["{}_Fri".format(student)] <= 2)

    # No more than 3 students can be scheduled for duty each day
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
        model.addConstr(
            variables["y"]["1_" + day] + variables["y"]["2_" + day] + variables["y"]["3_" + day] +
            variables["y"]["4_" + day] + variables["y"]["5_" + day] + variables["y"]["6_" + day] <= 3)

    # Availability constraints
    availability_hours = {
        1: {
            "Mon": 6,
            "Tue": 0,
            "Wed": 6,
            "Thu": 0,
            "Fri": 7
        },
        2: {
            "Mon": 0,
            "Tue": 8,
            "Wed": 9,
            "Thu": 6,
            "Fri": 0
        },
        3: {
            "Mon": 4,
            "Tue": 8,
            "Wed": 3,
            "Thu": 0,
            "Fri": 5
        },
        4: {
            "Mon": 5,
            "Tue": 5,
            "Wed": 6,
            "Thu": 0,
            "Fri": 4
        },
        5: {
            "Mon": 3,
            "Tue": 0,
            "Wed": 5,
            "Thu": 8,
            "Fri": 0
        },
        6: {
            "Mon": 0,
            "Tue": 6,
            "Wed": 0,
            "Thu": 6,
            "Fri": 5
        }
    }

    for student in [1, 2, 3, 4, 5, 6]:
        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            model.addConstr(variables["h"]["{}_{}".format(student, day)] <= availability_hours[student][day])

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
        return solution
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }