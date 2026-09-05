import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("recruitment_model")

    # Decision variables
    variables = {
        "x_1_Donghai_1": model.addVar(name="x_1_Donghai_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_Donghai_2": model.addVar(name="x_1_Donghai_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_Nanjiang_1": model.addVar(name="x_1_Nanjiang_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_Nanjiang_2": model.addVar(name="x_1_Nanjiang_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_Donghai_2": model.addVar(name="x_2_Donghai_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_Donghai_3": model.addVar(name="x_2_Donghai_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_Nanjiang_2": model.addVar(name="x_2_Nanjiang_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_Nanjiang_3": model.addVar(name="x_2_Nanjiang_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_Donghai_1": model.addVar(name="x_3_Donghai_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_Donghai_3": model.addVar(name="x_3_Donghai_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_Nanjiang_1": model.addVar(name="x_3_Nanjiang_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_Nanjiang_3": model.addVar(name="x_3_Nanjiang_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_Donghai_1": model.addVar(name="x_4_Donghai_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_Donghai_3": model.addVar(name="x_4_Donghai_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_Nanjiang_1": model.addVar(name="x_4_Nanjiang_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_Nanjiang_3": model.addVar(name="x_4_Nanjiang_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_Donghai_2": model.addVar(name="x_5_Donghai_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_Donghai_3": model.addVar(name="x_5_Donghai_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_Nanjiang_2": model.addVar(name="x_5_Nanjiang_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_Nanjiang_3": model.addVar(name="x_5_Nanjiang_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_6_Donghai_3": model.addVar(name="x_6_Donghai_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_6_Nanjiang_3": model.addVar(name="x_6_Nanjiang_3", vtype=GRB.CONTINUOUS, lb=0),
        "p3_shortfall": model.addVar(name="p3_shortfall", vtype=GRB.CONTINUOUS, lb=0)
    }

    # Objective function: P1, P2, P3
    model.setObjective(
        gp.quicksum(variables[f"x_{i}_Donghai_{j}"] for i in [1, 2, 3, 4, 5, 6] for j in [1, 2, 3]) +
        gp.quicksum(variables[f"x_{i}_Nanjiang_{j}"] for i in [1, 2, 3, 4, 5, 6] for j in [1, 2, 3]) -
        variables["p3_shortfall"],
        GRB.MAXIMIZE)

    # Demand constraints
    for specialty in [1, 2, 3]:
        if f"Donghai_{specialty}" in data["demand"]:
            model.addConstr(gp.quicksum(variables[f"x_{i}_Donghai_{specialty}"] for i in [1, 2, 3, 4, 5, 6]) >= data["demand"][f"Donghai_{specialty}"])
        if f"Nanjiang_{specialty}" in data["demand"]:
            model.addConstr(gp.quicksum(variables[f"x_{i}_Nanjiang_{specialty}"] for i in [1, 2, 3, 4, 5, 6]) >= data["demand"][f"Nanjiang_{specialty}"])

    # P2: Maximize the number of recruited personnel assigned to their preferred specialty
    model.addConstr(variables["x_1_Donghai_1"] + variables["x_2_Donghai_2"] + variables["x_3_Donghai_1"] + variables["x_4_Donghai_1"] + variables["x_5_Donghai_2"] >= 8000)
    model.addConstr(variables["x_1_Donghai_2"] + variables["x_2_Donghai_3"] + variables["x_3_Donghai_3"] + variables["x_4_Donghai_3"] + variables["x_5_Donghai_3"] >= 8000)
    model.addConstr(variables["x_1_Nanjiang_1"] + variables["x_2_Nanjiang_2"] + variables["x_3_Nanjiang_1"] + variables["x_4_Nanjiang_1"] + variables["x_5_Nanjiang_2"] >= 8000)
    model.addConstr(variables["x_1_Nanjiang_2"] + variables["x_2_Nanjiang_3"] + variables["x_3_Nanjiang_3"] + variables["x_4_Nanjiang_3"] + variables["x_5_Nanjiang_3"] + variables["x_6_Nanjiang_3"] >= 8000)

    # P3: Maximize the number assigned to their preferred city
    model.addConstr(variables["x_1_Donghai_1"] + variables["x_2_Donghai_2"] + variables["x_3_Donghai_1"] + variables["x_4_Donghai_1"] + variables["x_5_Donghai_2"] + variables["x_6_Donghai_3"] >= 8000)
    model.addConstr(variables["x_1_Nanjiang_1"] + variables["x_2_Nanjiang_2"] + variables["x_3_Nanjiang_1"] + variables["x_4_Nanjiang_1"] + variables["x_5_Nanjiang_2"] + variables["x_6_Nanjiang_3"] >= 8000)

    # Available people
    for i in [1, 2, 3, 4, 5, 6]:
        if i == 1:
            model.addConstr(variables["x_1_Donghai_1"] + variables["x_1_Donghai_2"] + variables["x_1_Nanjiang_1"] + variables["x_1_Nanjiang_2"] <= 1500)
        elif i == 2:
            model.addConstr(variables["x_2_Donghai_2"] + variables["x_2_Donghai_3"] + variables["x_2_Nanjiang_2"] + variables["x_2_Nanjiang_3"] <= 1500)
        elif i == 3:
            model.addConstr(variables["x_3_Donghai_1"] + variables["x_3_Donghai_3"] + variables["x_3_Nanjiang_1"] + variables["x_3_Nanjiang_3"] <= 1500)
        elif i == 4:
            model.addConstr(variables["x_4_Donghai_1"] + variables["x_4_Donghai_3"] + variables["x_4_Nanjiang_1"] + variables["x_4_Nanjiang_3"] <= 1500)
        elif i == 5:
            model.addConstr(variables["x_5_Donghai_2"] + variables["x_5_Donghai_3"] + variables["x_5_Nanjiang_2"] + variables["x_5_Nanjiang_3"] <= 1500)
        elif i == 6:
            model.addConstr(variables["x_6_Donghai_3"] + variables["x_6_Nanjiang_3"] <= 1500)

    # Suitable specialties
    for i in [1, 2, 3, 4, 5, 6]:
        if i == 1:
            model.addConstr(variables["x_1_Donghai_1"] + variables["x_1_Nanjiang_1"] <= 1500)
            model.addConstr(variables["x_1_Donghai_2"] + variables["x_1_Nanjiang_2"] <= 1500)
        elif i == 2:
            model.addConstr(variables["x_2_Donghai_2"] + variables["x_2_Nanjiang_2"] <= 1500)
            model.addConstr(variables["x_2_Donghai_3"] + variables["x_2_Nanjiang_3"] <= 1500)
        elif i == 3:
            model.addConstr(variables["x_3_Donghai_1"] + variables["x_3_Nanjiang_1"] <= 1500)
            model.addConstr(variables["x_3_Donghai_3"] + variables["x_3_Nanjiang_3"] <= 1500)
        elif i == 4:
            model.addConstr(variables["x_4_Donghai_1"] + variables["x_4_Nanjiang_1"] <= 1500)
            model.addConstr(variables["x_4_Donghai_3"] + variables["x_4_Nanjiang_3"] <= 1500)
        elif i == 5:
            model.addConstr(variables["x_5_Donghai_2"] + variables["x_5_Nanjiang_2"] <= 1500)
            model.addConstr(variables["x_5_Donghai_3"] + variables["x_5_Nanjiang_3"] <= 1500)
        elif i == 6:
            model.addConstr(variables["x_6_Donghai_3"] <= 1500)
            model.addConstr(variables["x_6_Nanjiang_3"] <= 1500)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_Donghai_1": variables["x_1_Donghai_1"].x,
            "x_1_Donghai_2": variables["x_1_Donghai_2"].x,
            "x_1_Nanjiang_1": variables["x_1_Nanjiang_1"].x,
            "x_1_Nanjiang_2": variables["x_1_Nanjiang_2"].x,
            "x_2_Donghai_2": variables["x_2_Donghai_2"].x,
            "x_2_Donghai_3": variables["x_2_Donghai_3"].x,
            "x_2_Nanjiang_2": variables["x_2_Nanjiang_2"].x,
            "x_2_Nanjiang_3": variables["x_2_Nanjiang_3"].x,
            "x_3_Donghai_1": variables["x_3_Donghai_1"].x,
            "x_3_Donghai_3": variables["x_3_Donghai_3"].x,
            "x_3_Nanjiang_1": variables["x_3_Nanjiang_1"].x,
            "x_3_Nanjiang_3": variables["x_3_Nanjiang_3"].x,
            "x_4_Donghai_1": variables["x_4_Donghai_1"].x,
            "x_4_Donghai_3": variables["x_4_Donghai_3"].x,
            "x_4_Nanjiang_1": variables["x_4_Nanjiang_1"].x,
            "x_4_Nanjiang_3": variables["x_4_Nanjiang_3"].x,
            "x_5_Donghai_2": variables["x_5_Donghai_2"].x,
            "x_5_Donghai_3": variables["x_5_Donghai_3"].x,
            "x_5_Nanjiang_2": variables["x_5_Nanjiang_2"].x,
            "x_5_Nanjiang_3": variables["x_5_Nanjiang_3"].x,
            "x_6_Donghai_3": variables["x_6_Donghai_3"].x,
            "x_6_Nanjiang_3": variables["x_6_Nanjiang_3"].x,
            "p3_shortfall": variables["p3_shortfall"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": solution["p3_shortfall"],
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }