import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("plastic_production_model")
    
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]
    
    # Decision variables
    produced = {}
    for i in range(6):
        produced[i] = model.addVar(name=f"produced_{i+1}", lb=0, vtype=GRB.CONTINUOUS)
    
    allocation = {}
    for i in range(6):
        for j in range(6):
            if cap[i] >= cap[j]:
                allocation[i, j] = model.addVar(name=f"allocation_{i+1}_{j+1}", lb=0, vtype=GRB.CONTINUOUS)
    
    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(vcost[i] * produced[i] for i in range(6)) +
        gp.quicksum(allocation[i, j] * vcost[j] for i in range(6) for j in range(6) if cap[i] >= cap[j]) +
        6 * fixed,
        GRB.MINIMIZE)

    # Demand constraint
    for i in range(6):
        model.addConstr(produced[i] + gp.quicksum(allocation[j, i] for j in range(6) if cap[j] >= cap[i]) >= dem[i])

    return model, {"produced": produced, "allocation": allocation}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "produced": {i+1: variables["produced"][i].x for i in range(6)},
                "allocation": { (i+1, j+1): variables["allocation"][i, j].x for i in range(6) for j in range(6) if data["cap"][i] >= data["cap"][j] }
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "produced": {},
                "allocation": {}
            }
        }

    return solution