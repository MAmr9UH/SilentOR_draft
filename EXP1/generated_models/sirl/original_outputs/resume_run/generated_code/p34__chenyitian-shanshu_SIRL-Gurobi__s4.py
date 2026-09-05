import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("raw_materials_transportation_model")
    
    trucks_A = model.addVar(name="trucks_A", vtype=GRB.INTEGER, lb=0)
    trucks_B = model.addVar(name="trucks_B", vtype=GRB.INTEGER, lb=0)
    
    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }
    
    # Raw material constraints
    model.addConstr(trucks_A * data["truck_contents"]["A"]["A"] + trucks_B * data["truck_contents"]["B"]["A"] >= 240)
    model.addConstr(trucks_A * data["truck_contents"]["A"]["B"] + trucks_B * data["truck_contents"]["B"]["B"] >= 80)
    model.addConstr(trucks_A * data["truck_contents"]["A"]["C"] + trucks_B * data["truck_contents"]["B"]["C"] >= 120)

    # Objective function: Minimize total freight cost
    model.setObjective(trucks_A * data["freight_cost"]["A"] + trucks_B * data["freight_cost"]["B"], GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "trucks_A": variables["trucks_A"].x,
                "trucks_B": variables["trucks_B"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "trucks_A": None,
                "trucks_B": None
            }
        }