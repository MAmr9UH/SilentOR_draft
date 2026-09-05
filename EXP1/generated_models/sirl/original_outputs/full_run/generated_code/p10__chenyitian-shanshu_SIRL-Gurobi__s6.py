import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("gandhi_clothing_model")
    
    shirts = model.addVar(name="shirts", vtype=GRB.CONTINUOUS, lb=0)
    shorts = model.addVar(name="shorts", vtype=GRB.CONTINUOUS, lb=0)
    pants = model.addVar(name="pants", vtype=GRB.CONTINUOUS, lb=0)
    
    y_shirts = model.addVar(name="y_shirts", vtype=GRB.BINARY)
    y_shorts_m = model.addVar(name="y_shorts_m", vtype=GRB.BINARY)
    y_pants = model.addVar(name="y_pants", vtype=GRB.BINARY)
    
    # Labor constraint
    model.addConstr(shirts * data["labor_per_unit"]["shirts"] + shorts * data["labor_per_unit"]["shorts"] + pants * data["labor_per_unit"]["pants"] <= data["labor_available"])
    
    # Cloth constraint
    model.addConstr(shirts * data["cloth_per_unit"]["shirts"] + shorts * data["cloth_per_unit"]["shorts"] + pants * data["cloth_per_unit"]["pants"] <= data["cloth_available"])
    
    # Rental cost
    model.addConstr(data["rental_cost"]["shirts"] * y_shirts + data["rental_cost"]["shorts"] * y_shorts_m + data["rental_cost"]["pants"] * y_pants >= 0)
    
    # Machinery rental indicator
    model.addConstr(shirts * 100000 * y_shirts >= shirts)
    model.addConstr(shorts * 100000 * y_shorts_m >= shorts)
    model.addConstr(pants * 100000 * y_pants >= pants)
    
    # Objective function: Maximize profit
    model.setObjective(
        (shirts * (data["unit_contribution"]["shirts"] - data["rental_cost"]["shirts"] * y_shirts) +
         shorts * (data["unit_contribution"]["shorts"] - data["rental_cost"]["shorts"] * y_shorts_m) +
         pants * (data["unit_contribution"]["pants"] - data["rental_cost"]["pants"] * y_pants)),
        GRB.MAXIMIZE)
    
    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "shirts": variables["shirts"].x,
                "shorts": variables["shorts"].x,
                "pants": variables["pants"].x,
                "y_shirts": variables["y_shirts"].x,
                "y_shorts_m": variables["y_shorts_m"].x,
                "y_pants": variables["y_pants"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "shirts": None,
                "shorts": None,
                "pants": None,
                "y_shirts": None,
                "y_shorts_m": None,
                "y_pants": None
            }
        }