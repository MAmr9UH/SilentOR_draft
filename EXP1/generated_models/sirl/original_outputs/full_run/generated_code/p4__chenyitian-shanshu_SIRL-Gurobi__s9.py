import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("nutritional_model")
    
    # Define decision variables
    variables = {}
    for food in data["foods"]:
        variables[food] = model.addVar(name=food, vtype=GRB.CONTINUOUS, lb=0)

    # Protein constraint
    model.addConstr(gp.quicksum(data["protein"][food] * variables[food] for food in data["foods"]) >= data["min"]["protein"])

    # Carbohydrate constraint
    model.addConstr(gp.quicksum(data["carb"][food] * variables[food] for food in data["foods"]) >= data["min"]["carb"])

    # Calories constraint
    model.addConstr(gp.quicksum(data["calories"][food] * variables[food] for food in data["foods"]) >= data["min"]["calories"])

    # Objective function: Minimize total cost
    model.setObjective(gp.quicksum(data["cost"][food] * variables[food] for food in data["foods"]), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "chicken": variables["chicken"].x,
            "rice": variables["rice"].x,
            "broccoli": variables["broccoli"].x,
            "tofu": variables["tofu"].x,
            "beans": variables["beans"].x
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